const joi=require('joi');

const signupValidation=(req,res,next)=>{
  const schema=joi.object({
    name:joi.string().required().max(100),
    email:joi.string().required().email().max(100),
    password:joi.string().required().min(4).max(100),
  });
  const {error}=schema.validate(req.body);

  if(error){
    return res.status(400).json({message:"Invalid Request!!!",error})
  }
  next();
}
const loginValidation=(req,res,next)=>{
  const schema=joi.object({
    email:joi.string().required().email().max(100),
    password:joi.string().required().min(4).max(100),
  });
  const {error}=schema.validate(req.body);

  if(error){
    return res.status(400).json({message:"Invalid Request!!!",error})
  }
  next();
}

module.exports={signupValidation,loginValidation};