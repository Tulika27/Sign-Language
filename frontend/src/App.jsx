import { useState } from 'react'
import './App.css'
import Home from './pages/Home/Home'
import { Routes, Route, Navigate } from 'react-router-dom'
import SignUp from './pages/Auth/SignUp'
import Login from './pages/Auth/Login'
import { ToastContainer, toast } from 'react-toastify';
import Test from './pages/TestPage/Test'
import HandleRefresh from './Components/HandleRefresh'
import NumberTest from './pages/Module/NumberTest'
import AlphaTest from './pages/Module/AlphaTest'
import Account from './pages/Profile/Account'
import Result from './Components/Result'
import UserContextProvider from './Context/UserContextProvider'
import Dashboard from './pages/Profile/Dashboard'
import PageNotFound from './Components/PageNotFound'
import IndianSignTest from './pages/Module/IndianSignTest'
import Forgot from './pages/Auth/Forgot'
import ResetPassword from './pages/Auth/ResetPassword'


function App() {
  const [isAuth, setIsAuth] = useState(false);
  const PrivateRoute = ({ element }) => {
    return isAuth ? element : <Navigate to='/login' />
  }

  return (
    <>
      <HandleRefresh setIsAuth={setIsAuth} />
        <UserContextProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/home" />} />
            <Route path='/home' element={<Home/>} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/forgot-password" element={<Forgot/>}/>
            <Route path="/reset-password/:token" element={<ResetPassword />} />

            <Route path="/test" element={<PrivateRoute element= {<Test />} />} >
            </Route>
            
            <Route path='/test'>
                <Route path='/test/numbertest'
                  element={<PrivateRoute element={<NumberTest />}/>} />
                <Route path='/test/islTest'
                  element={<PrivateRoute element={<IndianSignTest />}/>} />
                <Route path='/test/alphabet'
                element={<PrivateRoute element={<AlphaTest />}/>} />
             </Route>


            <Route path="/alpha-result"
              element={<PrivateRoute element={<Result category={'Alphabet'} totalSign={26} />} />} />

            <Route path="/isl-result"
              element={<PrivateRoute element={<Result category={'Indian Alphabet'} totalSign={26} />} />} />

            <Route path="/number-result"
              element={<PrivateRoute element={<Result category={'Number'} totalSign={10} />} />} />

            <Route path="/account"
              element={<PrivateRoute element={<Account />} />} />

            <Route path="/history"
              element={<PrivateRoute element={<Dashboard />} />} />
              
            <Route path='/*' element={<PageNotFound />} />
          </Routes>
          
        </UserContextProvider>
        <ToastContainer />
    </>
  )
}

export default App
