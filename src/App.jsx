import { useState, createContext } from 'react'
import reactLogo from './assets/react.svg'

import './App.css'
import 'bootstrap/dist/css/bootstrap.min.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardContent from './components/dashboard/DashboardContent';
import Login from './components/Login';
import DeviceDetail from './components/DeviceDetail';
import DeviceList from './components/DeviceList';
import Dashboard from './components/dashboard/Dashboard';
import DeviceDetailChart from './components/DeviceDetailChart';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DeviceDetailGraph from './components/DeviceDetailGraph';
import LoginPage from './pages/LoginPage';
import PrivateRoute from './components/PrivateRoute';
import DeviceSocket from './components/DeviceSocket';


const queryClient = new QueryClient();
export const MyContext=createContext();

function App() {

  const [isHideSidebarAndHeader , setIsHideSidebarAndHeader]=useState(true);
  
  const [isClick, setIsClick]=useState(1);
   const [toggleSidebar , setToggleSidebar]=useState(true);

  const values={

    isHideSidebarAndHeader,
    setIsHideSidebarAndHeader,
    isClick,
    setIsClick,
    toggleSidebar,
    setToggleSidebar,
  
  }

  return (
    <QueryClientProvider client={queryClient}>
        <BrowserRouter>

        
           <MyContext.Provider value={values}>
              { isHideSidebarAndHeader!==false && 
                <Header />
              }
              <Routes>
        <Route path='/login' element={<Login />} ></Route>
        
           
        

        </Routes>
    

           <Routes>
            <Route path='/connexion' element={<LoginPage />} ></Route>
          </Routes>
        <div className="main d-flex">
        {isHideSidebarAndHeader!==false &&
          <div className={`sidebarWrapper ${toggleSidebar ? 'visible' : 'hide'}`}>
           
              <Sidebar /> 
            
          </div>
          }

          
        <div className="content">
           

        
        <Routes>
        
      
        {/*} <Route path='/' element={<DashboardContent />} ></Route> */}
        <Route path='/' element={ <PrivateRoute> <Dashboard /> </PrivateRoute>} ></Route>
          <Route path='/device/:id' element={<DeviceDetail />} ></Route>
          <Route path='/appareils' element={<PrivateRoute> <DeviceList /> </PrivateRoute>} ></Route>
          <Route path='/appareils_chart/:id' element={<DeviceDetailGraph />} ></Route>
           
           <Route path='/devicesocket/:id' element={<DeviceSocket />} ></Route>
          
          
          
        </Routes>
       
        </div>
                
        </div>
          
        </MyContext.Provider >
        
        </BrowserRouter>
        </QueryClientProvider>
        
  )
}

export default App
