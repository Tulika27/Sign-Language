import React from 'react'

function Footer() {
  return (
    <>
     <footer className="bg-blue-600 text-white p-4 mt-8">
      <div className="container mx-auto flex flex-col md:flex-row justify-between items-center">
        {/* Left Section - Copyright */}
        <p className="text-center md:text-left">
          &copy; {new Date().getFullYear()} Testing App. All rights reserved.
        </p>

        {/* Right Section - Links */}
        <div className="flex space-x-4 mt-2 md:mt-0">
          <a href="#" className="hover:text-gray-200">
            Privacy Policy
          </a>
          <a href="#" className="hover:text-gray-200">
            Terms of Service
          </a>
          <a href="#" className="hover:text-gray-200">
            Contact
          </a>
        </div>
      </div>
    </footer>
    


    </>
  )
}

export default Footer
