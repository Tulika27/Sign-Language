const mongoose = require("mongoose");
const schema=mongoose.Schema;

const UserSchema=new schema({
  name:{type:String,require:true},
  email:{type:String,require:true,unique:true},
  password:{type:String,require:true},
});

const userModel=mongoose.model('users',UserSchema);

module.exports=userModel;