import React, { useEffect, useState } from 'react'
import Buttons from '../../Components/Buttons';
import { useNavigate,Outlet } from 'react-router-dom';
import NewNavbar from '../../Components/NewNavbar';
import Footer from '../../Components/Footer';
import TestField from '../../Components/TestField';

function Test() {
  const [user, setUser] = useState('');
  useEffect(() => {
    setUser(localStorage.getItem('userName'))
  }, [])

  const navigate = useNavigate();

  const handleLogout = (e) => {
    localStorage.removeItem('token');
    localStorage.removeItem('userName');
    setTimeout(() => {
      navigate('/home');
    }, 1000)
  }
  return (
    <>
      <NewNavbar element={<Buttons name='Log Out' />} />
        <h1 className='text-center font-extrabold text-4xl text-blue-500'>Test Modules</h1>
        <div className=' flex flex-wrap justify-center gap-10  '>
          <TestField 
          image='src\assets\number.jpg'
          heading='Number Test' subHeading='Test Sign Language Number' 
          linkTo='/test/numbertest'
          lockTo={false} />

            <TestField 
            image='src/assets/signAlpha.jpg'
            heading='Alphabet Test' subHeading='Test Sign Language Alphabet '
            linkTo='/test/alphabet'
            lockTo={false}
            />

            <TestField 
            image='src/assets/IndianAlpha.jpg'
            heading='Indian Sign Test' subHeading='Test Sign Language Alphabet in India '
            linkTo='/test/islTest'
            lockTo={false}
            />

            <TestField
             image='src/assets/basicword.jpg'
             heading='Basic Word Test' subHeading='Test Basic word using Sign Language' 
            linkTo='/bwordtest'
            />

            <TestField 
             image='src/assets/wh.jpg'
            heading='WH Question Test' subHeading='Test your question word using sign language' 
            linkTo='/iwordtest'
            />
            <TestField 
            image='src/assets/basicSentence.jpg'
            heading='Basic Sentence Test' subHeading='Test small sentence using sign language' 
            linkTo='/bsentencetest'/>
         
            <TestField 
            image='src/assets/talk.jpg'
            heading='Basic Conversation Test' 
            subHeading='Test basic conversation using sign language'
            linkTo='/bconversationtest' />


        </div>
        <Footer />
        <Outlet/>
    </>
  )
}

export default Test
