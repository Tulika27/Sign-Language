const { PDFDocument, rgb } = require("pdf-lib");
const fs = require("fs");
const fontkit = require("fontkit");
const path = require("path");

const generateCertificate = async (req, res) => {
  try {
    const { name, course } = req.body;
    if (!name || !course) {
      return res.status(400).json({ error: "Name and course are required." });
    }

    const templatePath = path.join(__dirname, "..", "certificates", "certificate_template.pdf");
    const fontPath = path.join(__dirname, "..", "fonts", "CopperPennyDTP.ttf");

    // Debugging file existence
    if (!fs.existsSync(templatePath)) {
      return res.status(404).json({ error: "Certificate template file not found." });
    }

    if (!fs.existsSync(fontPath)) {
      return res.status(404).json({ error: "Custom font file not found." });
    }

    const existingPdfBytes = fs.readFileSync(templatePath);
    const customFontBytes = fs.readFileSync(fontPath);

    const pdfDoc = await PDFDocument.load(existingPdfBytes);
    pdfDoc.registerFontkit(fontkit);

    const customFont = await pdfDoc.embedFont(customFontBytes);
    const pages = pdfDoc.getPages();
    const firstPage = pages[0];

    // Centered text drawing
    const drawCenteredText = (page, text, y, font, maxWidth, initialFontSize = 36, minFontSize = 12, color = rgb(0, 0, 0)) => {
      let fontSize = initialFontSize;
      let textWidth = font.widthOfTextAtSize(text, fontSize);
      while (textWidth > maxWidth && fontSize > minFontSize) {
        fontSize--;
        textWidth = font.widthOfTextAtSize(text, fontSize);
      }
      const x = (page.getSize().width - textWidth) / 2;
      page.drawText(text, { x, y, size: fontSize, font, color });
    };

    const date = new Date().toLocaleDateString();
    const certId = "CERT-" + Date.now();

    drawCenteredText(firstPage, name, 240, customFont, 500);
    drawCenteredText(firstPage, course, 150, customFont, 500, 28);

    firstPage.drawText(date, { x: 740, y: 20, size: 14, font: customFont, color: rgb(0.3, 0.3, 0.3) });
    firstPage.drawText(certId, { x: 20, y: 20, size: 14, font: customFont, color: rgb(0.3, 0.3, 0.3) });

    const pdfBytes = await pdfDoc.save();

    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", "attachment; filename=certificate.pdf");
    res.send(Buffer.from(pdfBytes));

  } catch (err) {
    console.error("Certificate Generation Error:", err);
    res.status(500).json({ error: "Internal server error during certificate generation." });
  }
};

module.exports = { generateCertificate };
