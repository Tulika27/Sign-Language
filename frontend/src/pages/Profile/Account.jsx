import React from 'react'
import Dashboard from './Dashboard'
import NewNavbar from '../../Components/NewNavbar'
import Footer from '../../Components/Footer'
import { Link } from 'react-router-dom';

function Account() {
  const user=localStorage.getItem('userName');
  return (
    <>
      <NewNavbar/>
      <Link to='/history'>
        History
      </Link>
      <Footer/>
    </>
  )
}

export default Account
