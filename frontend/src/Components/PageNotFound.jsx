import React from 'react'
import Navbar from './Navbar'
import { Link } from 'react-router-dom'
import Footer from './Footer'

function PageNotFound() {
  return (
    <>
      <div className='flex flex-col justify-between  h-screen'>
      <Navbar/>
      <div className='flex flex-col
       items-center gap-10 '>
        <img className="font-bold text-6xl text-center text-blue-500  z-1" src="\src\assets\pageNotFound.png" alt="404" srcset="" />
        <div className='bg-blue-500 hover:bg-blue-600 text-gray-100 p-3 pl-5 pr-5 z-10 flex justify-center  items-center font-semibold rounded-xl text-center text-lg cursor-pointer'>
          <Link to="/">🏠 Home</Link>
        </div>
      </div>
        <Footer/>
      </div>
    </>
    
  )
}

export default PageNotFound
