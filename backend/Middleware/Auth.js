const jwt=require('jsonwebtoken');
const ensureAuth=(req,res,next)=>{
  const auth=req.headers['authorization'];
  if(!auth){
    return res.status(403)
      .json({
        message:"jwt Token is required!!"
      })
  }
  try {
    const decode=jwt.verify(auth,process.env.JWT_SECRET);
    req.user=decode;
    next();
  } catch (error) {
    return res.status(403)
     .json({
      message:"Unauthorize Access !!"
     })
  }
}

module.exports=ensureAuth;