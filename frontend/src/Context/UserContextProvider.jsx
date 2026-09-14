import React ,{useEffect, useState} from 'react'
import UserContext from './UserContext'

function UserContextProvider({children}) {
  const [correct,setCorrect]=useState(0);
  return (
    <UserContext.Provider value={{correct,setCorrect}}>
      {children}
    </UserContext.Provider>
  )
}

export default UserContextProvider
