const express = require("express");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const {loginValidation,signupValidation}=require("../Middleware/AuthValidation");
const {signupController,loginController } = require("../Controller/AuthController");

const {forgotController,resetPasswordController}=require('../Controller/forgot-password')

const router = express.Router();

// Login Route
router.post('/login',loginValidation,loginController);

// Signup Route
router.post('/signup',signupValidation,signupController);

router.post('/forgot-password',forgotController);

router.post('/reset-password',resetPasswordController);



module.exports = router;
