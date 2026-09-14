const bcrypt=require('bcrypt');
const userModel=require('../Models/User');
const jwt=require('jsonwebtoken')

const signupController=async(req,res)=>{
    try {
      const { name, email, password } = req.body;
      let user = await userModel.findOne({ email });
      if (user) return res.status(400).json({ message: "User already exists" });
  
      const salt = await bcrypt.genSalt(10);
      const hashedPassword = await bcrypt.hash(password, salt);
  
      user = new userModel({ name, email, password: hashedPassword });
      await user.save();
      res.status(201)
        .json({
          message:"SignUp Successfully !!",
          success:true
        })
  
      // const token = jwt.sign({ userId: user._id }, process.env.JWT_SECRET, {
      //   expiresIn: "1h",
      // });
      // res.status(201).json({ token, message: "Signup successful" });

    } catch (err) {
      res.status(500).json({
         message:"Controller Error!",
         success:false
       });
    }
  };

  const loginController=async (req, res) => {
    try {
      const { email, password } = req.body;
  
      const user = await userModel.findOne({ email });
      if (!user) return res.status(400).json({ message: "User Not Exist!!" });
  
      const isMatch = await bcrypt.compare(password, user.password);
      if (!isMatch) return res.status(400).json({ message: "Invalid credentials" });

      const userId = user._id;
  
      const token = jwt.sign({ userId: user._id }, process.env.JWT_SECRET,
         {expiresIn: "1h"}
      );
      res.status(201)
        .json({
          message: "Login successful",
          success:true,
          jwtToken:token,
          userName:user.name,
          userId:userId
        });
    } catch (error) {
      console.log(error);
      res.status(500).json({ message: "Server error" });
    }
  };

  module.exports={signupController,loginController};