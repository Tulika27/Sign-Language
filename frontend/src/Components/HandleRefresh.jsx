import React, { useEffect } from 'react'
import { replace, useLocation, useNavigate } from 'react-router-dom'

function HandleRefresh({setIsAuth}) {
  const location=useLocation();
  const navigate=useNavigate();

  useEffect(()=>{
    if(localStorage.getItem('token')){
      setIsAuth(true);
      if(location.pathname==='/'
        ||location.pathname==='/login'|| location.pathname==='/signup'
      ){
        navigate('/test',{replace:false})
      }
    }else{
      setIsAuth(false);
    }

  },[location,navigate,setIsAuth])

  return (
    <>
    </>
  )
}

export default HandleRefresh
