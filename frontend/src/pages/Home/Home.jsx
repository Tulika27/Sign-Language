import React from 'react'
import Footer from '../../Components/Footer'
import Buttons from '../../Components/Buttons'
import { useNavigate } from 'react-router-dom'
import NewNavbar from '../../Components/NewNavbar'

function Home() {
  const navigate=useNavigate();
  return (
    <>

      <div className='flex flex-col h-screen justify-between'>
       <NewNavbar element={<Buttons name='Log Out' />} />
      <div 
      style={{
        backgroundImage: `url(./src/assets/homepage.jpg)`,
        backgroundRepeat:"no-repeat"
      }}
      className="bg-contain lg:min-h-screen bg-white">
        <div className='block lg:w-140 w-50 md:w-90 sm:w-90 sm:pt-20 sm:pl-10 p-5 lg:pt-30 lg:pl-30
        md:pl-15 md:pt-15 '>
          <p className="sm:text-3xl lg:text-5xl 
          text-xl
          font-sans font-bold text-blue-600">
            Test Your Sign Language Skill
          </p>
         
          <p className='lg:text-2xl 
          md:text-xl
          text md:pt-5
          font-semibold text-gray-500 w-fit'>Learning sign language is not just about communication; it's about inclusion, empathy, and breaking barriers !</p>
          
          <button className='pt-10' onClick={() => navigate('/login')}>
            <Buttons name="Get Started"/>
          </button>
        </div>
          {/* <img 
          className='flex justify-center items-center w-screen pt-40 p-30'
          src="/src/assets/slider.png" alt="" srcset="" /> */}
      </div>  
     
      <Footer/>
      </div>
    </>
  )
}

export default Home
