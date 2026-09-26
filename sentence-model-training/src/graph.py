"""
Landmark Graph and Adjacency Matrix Builder for ST-GCN.
Constructs spatial graph topology for 543 MediaPipe Holistic landmarks (Pose + Face + Hands).
"""

import numpy as np
import torch
from typing import List, Tuple


class LandmarkGraph:
    """
    Graph topology for 543 MediaPipe Holistic landmarks:
        - Pose: 33 landmarks [indices 0..32]
        - Face: 468 landmarks [indices 33..500]
        - Left Hand: 21 landmarks [indices 501..521]
        - Right Hand: 21 landmarks [indices 522..542]
    """

    NUM_NODES = 543

    def __init__(self, strategy: str = "spatial", max_hop: int = 1):
        self.max_hop = max_hop
        self.strategy = strategy
        self.edges = self._get_edges()
        self.A = self._get_adjacency_matrix()

    def _get_edges(self) -> List[Tuple[int, int]]:
        edges = []

        # ---------------------------------------------------------------------
        # 1. Pose connections (33 landmarks: 0..32)
        # ---------------------------------------------------------------------
        pose_pairs = [
            # Head / Face keypoints on pose
            (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
            (9, 10),
            # Torso & Shoulders
            (11, 12), (11, 23), (12, 24), (23, 24),
            # Arms
            (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
            (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
            # Lower body (if present in frame)
            (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
            (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
        ]
        edges.extend(pose_pairs)

        # ---------------------------------------------------------------------
        # 2. Hand connections (21 landmarks each)
        # ---------------------------------------------------------------------
        hand_pairs = [
            # Thumb
            (0, 1), (1, 2), (2, 3), (3, 4),
            # Index
            (0, 5), (5, 6), (6, 7), (7, 8),
            # Middle
            (0, 9), (9, 10), (10, 11), (11, 12),
            # Ring
            (0, 13), (13, 14), (14, 15), (15, 16),
            # Pinky
            (0, 17), (17, 18), (18, 19), (19, 20),
            # Palm base
            (5, 9), (9, 13), (13, 17)
        ]

        # Left hand (offset = 501)
        lh_offset = 501
        for u, v in hand_pairs:
            edges.append((lh_offset + u, lh_offset + v))

        # Right hand (offset = 522)
        rh_offset = 522
        for u, v in hand_pairs:
            edges.append((rh_offset + u, rh_offset + v))

        # ---------------------------------------------------------------------
        # 3. Inter-component connections: Connect Wrists to Hands
        # ---------------------------------------------------------------------
        # Pose left wrist is index 15 -> Left hand wrist is index 501
        edges.append((15, 501))
        # Pose right wrist is index 16 -> Right hand wrist is index 522
        edges.append((16, 522))

        # Pose nose is index 0 -> Face mesh center anchor (e.g. index 33 + 1 = 34)
        edges.append((0, 34))

        # ---------------------------------------------------------------------
        # 4. Face mesh contour sample connections (subset of 468 landmarks)
        # ---------------------------------------------------------------------
        face_offset = 33
        # Connect sequential face boundary landmarks to form graph neighborhood
        face_step = 4  # Sparse connectivity to maintain computation efficiency
        for i in range(0, 468 - face_step, face_step):
            edges.append((face_offset + i, face_offset + i + face_step))

        return edges

    def _get_adjacency_matrix(self) -> np.ndarray:
        """
        Builds the normalized adjacency matrix partitioned for ST-GCN:
            Partition 0: Self-loops (Identity)
            Partition 1: Inward / Neighbor connections
            Partition 2: Outward / Extended connections (if spatial strategy)
        """
        num_node = self.NUM_NODES
        A_raw = np.zeros((num_node, num_node), dtype=np.float32)

        for u, v in self.edges:
            if u < num_node and v < num_node:
                A_raw[u, v] = 1.0
                A_raw[v, u] = 1.0

        if self.strategy == "spatial":
            # 3-partition spatial configuration
            # 0: self, 1: neighbors
            I = np.eye(num_node, dtype=np.float32)
            
            # Normalize neighbor matrix: D^(-1/2) * A * D^(-1/2)
            D = np.sum(A_raw, axis=1)
            D[D == 0] = 1.0
            D_inv_sqrt = np.power(D, -0.5)
            D_inv_sqrt[np.isinf(D_inv_sqrt)] = 0.0
            D_mat = np.diag(D_inv_sqrt)
            A_norm = D_mat @ A_raw @ D_mat

            # Construct 3 partitions: [Self-loops, Inward/Direct, Higher-order/Diffuse]
            A_self = I
            A_direct = A_norm
            A_diffuse = (A_norm @ A_norm) * (1.0 - I)
            
            A = np.stack([A_self, A_direct, A_diffuse], axis=0)  # Shape: (3, V, V)
        else:
            # Simple identity + normalized adjacency
            I = np.eye(num_node, dtype=np.float32)
            A_with_self = A_raw + I
            D = np.sum(A_with_self, axis=1)
            D_mat = np.diag(np.power(D, -1.0))
            A = np.expand_dims(D_mat @ A_with_self, axis=0)  # Shape: (1, V, V)

        return A

    def get_torch_adjacency(self) -> torch.Tensor:
        """Return adjacency matrix as a PyTorch FloatTensor (K, V, V)."""
        return torch.from_numpy(self.A).float()
