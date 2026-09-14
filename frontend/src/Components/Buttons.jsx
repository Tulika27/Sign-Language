import React from 'react'

function Buttons({name="Click Me"}) {
  return (
    <>
  
    <div>
      <div type="button"  className="text-white bg-gradient-to-br from-blue-600 to-blue-600 hover:bg-gradient-to-bl focus:ring-4 focus:outline-none focus:ring-blue-400 dark:focus:ring-blue-400 font-medium rounded-lg text-sm px-5 py-2.5 text-center me-2 mb-2 cursor-pointer">{name}</div>
    </div>
    </>
  )
}

export default Buttons
