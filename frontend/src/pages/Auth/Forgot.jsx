import react from 'react'
import {useState} from 'react'
import { toast } from "react-toastify";
import Navbar from '../../Components/Navbar';

function Forgot() {
  const [email, setEmail] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    try{
      const res = await fetch("http://localhost:5001/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    
    const data = await res.json();
    
    if (res.ok) {
      toast.success(data.message || "Reset link sent to your email");
    } else {
      toast.error(data.message || "Something went wrong");
    }
  } catch (err) {
    toast.error("Server error");
  }
    
  };

  return (

    <>
      <div className='bg-gray-800'>
        <Navbar/>
      </div>
      <div className='h-screen flex justify-center items-center flex-wrap flex-col bg-gray-100'>
      <div className='flex flex-col gap-2 w-99 items-center h-56 shadow-2xl rounded-2xl bg-white'>
        <h1 className='text-2xl font-bold text-cyan-800 m-3'>Forgot Password</h1>
        <form onSubmit={handleSubmit} className=' flex flex-col items-center'>
           <input 
           className='mb-5 text-l bg-gray-200 rounded-2xl p-3 w-80'
          type="email"
          placeholder='Enter your email'
          value={email}
          onChange={(e)=>setEmail(e.target.value)}
          />
           <button
              type="submit"
              className='bg-cyan-600 w-25 rounded-2xl h-10 font-bold text-amber-50'
              >
            Send
           </button>
        </form>
      </div>
    </div>

    </>
    
  )
}

export default Forgot
