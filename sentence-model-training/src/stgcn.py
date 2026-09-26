"""
Spatio-Temporal Graph Convolutional Network (ST-GCN) for 543 Landmarks.
Preserves the temporal sequence dimension for downstream Transformer & CTC sequence modeling.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from .graph import LandmarkGraph


class GraphConvolution(nn.Module):
    """
    Spatial Graph Convolution layer operating over partitioned skeletal graph.
    """

    def __init__(self, in_channels: int, out_channels: int, num_subsets: int = 3, bias: bool = True):
        super().__init__()
        self.num_subsets = num_subsets
        self.conv = nn.Conv2d(
            in_channels,
            out_channels * num_subsets,
            kernel_size=(1, 1),
            padding=(0, 0),
            stride=(1, 1),
            dilation=(1, 1),
            bias=bias,
        )

    def forward(self, x: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input feature map (N, C, T, V)
            A: Partitioned Adjacency matrix (K, V, V) where K = num_subsets
        Returns:
            Output feature map (N, C_out, T, V)
        """
        # Linear projection along channel dimension
        x = self.conv(x)  # (N, C_out * K, T, V)
        N, KC, T, V = x.size()
        K = self.num_subsets
        C_out = KC // K

        x = x.view(N, K, C_out, T, V)
        # Aggregate spatial neighbors via einsum: (N, K, C_out, T, V) x (K, V, W) -> (N, C_out, T, W)
        x = torch.einsum("nkctv,kvw->nctw", x, A)
        return x.contiguous()


class TemporalConvolution(nn.Module):
    """
    Temporal Convolution layer processing features across consecutive frames.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 9,
        stride: int = 1,
        dilation: int = 1,
        dropout: float = 0.0,
    ):
        super().__init__()
        padding = ((kernel_size - 1) * dilation) // 2
        self.conv = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size=(kernel_size, 1),
            padding=(padding, 0),
            stride=(stride, 1),
            dilation=(dilation, 1),
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.bn(self.conv(x)))


class STGCNBlock(nn.Module):
    """
    ST-GCN unit combining Spatial Graph Convolution and Temporal 1D Convolution with Residual.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        temporal_kernel_size: int = 9,
        stride: int = 1,
        dropout: float = 0.1,
        num_subsets: int = 3,
        residual: bool = True,
    ):
        super().__init__()
        self.gcn = GraphConvolution(in_channels, out_channels, num_subsets=num_subsets)
        self.tcn = TemporalConvolution(
            out_channels,
            out_channels,
            kernel_size=temporal_kernel_size,
            stride=stride,
            dropout=dropout,
        )
        self.relu = nn.ReLU(inplace=True)

        if not residual:
            self.residual = nn.Identity()
        elif (in_channels == out_channels) and (stride == 1):
            self.residual = nn.Identity()
        else:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=(1, 1), stride=(stride, 1)),
                nn.BatchNorm2d(out_channels),
            )

    def forward(self, x: torch.Tensor, A: torch.Tensor) -> torch.Tensor:
        res = self.residual(x)
        x = self.gcn(x, A)
        x = self.tcn(x)
        x = self.relu(x + res)
        return x


class STGCNEncoder(nn.Module):
    """
    Modular ST-GCN Feature Extractor.
    Processes input landmarks (N, C=3, T, V=543) and produces temporal frame embeddings (N, T, d_model).
    """

    def __init__(
        self,
        in_channels: int = 3,
        hidden_channels: int = 64,
        out_channels: int = 256,
        num_layers: int = 2,
        temporal_kernel_size: int = 9,
        dropout: float = 0.1,
    ):
        super().__init__()
        # Build landmark graph topology
        self.graph = LandmarkGraph(strategy="spatial")
        self.register_buffer("A", self.graph.get_torch_adjacency())  # Shape: (3, 543, 543)

        num_subsets = self.graph.A.shape[0]

        # Initial batch norm for coordinates
        self.data_bn = nn.BatchNorm1d(in_channels * self.graph.NUM_NODES)

        # ST-GCN Stack
        layers = []
        curr_in = in_channels
        curr_out = hidden_channels

        for i in range(num_layers):
            layers.append(
                STGCNBlock(
                    in_channels=curr_in,
                    out_channels=curr_out,
                    temporal_kernel_size=temporal_kernel_size,
                    stride=1,
                    dropout=dropout,
                    num_subsets=num_subsets,
                    residual=True,
                )
            )
            curr_in = curr_out
            if i == 0 and num_layers > 1:
                curr_out = hidden_channels * 2

        self.stgcn_blocks = nn.ModuleList(layers)

        # Spatial pooling / projection from (N, C_last, T, V) to (N, T, out_channels)
        self.spatial_pool = nn.AdaptiveAvgPool2d((None, 1))  # (N, C, T, 1)
        self.out_projection = nn.Sequential(
            nn.Linear(curr_in, out_channels),
            nn.LayerNorm(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input landmark tensor (N, C, T, V) = (N, 3, T, 543)
        Returns:
            Temporal frame features: (N, T, out_channels)
        """
        N, C, T, V = x.size()

        # Input landmark normalization
        x_norm = x.permute(0, 1, 3, 2).contiguous().view(N, C * V, T)
        x_norm = self.data_bn(x_norm)
        x = x_norm.view(N, C, V, T).permute(0, 1, 3, 2).contiguous()  # Back to (N, C, T, V)

        # Pass through ST-GCN blocks
        for block in self.stgcn_blocks:
            x = block(x, self.A)

        # Spatial aggregation: Pool over nodes V -> (N, C_feat, T, 1)
        x = self.spatial_pool(x).squeeze(-1)  # (N, C_feat, T)

        # Permute to (N, T, C_feat) and project to out_channels (d_model)
        x = x.permute(0, 2, 1).contiguous()   # (N, T, C_feat)
        out = self.out_projection(x)          # (N, T, out_channels)
        return out
