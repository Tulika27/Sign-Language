const express = require('express');
const {generateCertificate} =require("../Controller/certificateController");

const router = express.Router();

router.post('/download',generateCertificate);

module.exports = router;
