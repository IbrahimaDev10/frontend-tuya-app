import React from 'react'
import logo from '../assets/images/ns1.png'
import sertec_logo from "../assets/images/sertec_logo.jpeg"
import { IoMdMenu } from "react-icons/io";
import { Button } from '@mui/material';
import { SearchOff } from '@mui/icons-material';
import SearchBox from './SearchBox';
import { CiLight } from "react-icons/ci";
import { MdTextsms } from "react-icons/md";
import { IoNotifications } from "react-icons/io5";
import { FaUser } from "react-icons/fa";
import { MyContext } from '../App';
import { useContext } from 'react';

export default function Header() {
   const { toggleSidebar, setToggleSidebar } = useContext(MyContext);
  return (
    <header className='w-100 d-flex align-items-center'>
        <div className='container-fluid'>
            <div className='row align-items-center'>
                <div className='col-lg-2 d-flex align-items-center part1'>
                   <div className='d-flex align-items-center logo '>
                    <img className='logo_sertec' src={sertec_logo} alt="" />
                    
                    </div>
                    
                   
                   
                </div>
                <div className="col-lg-3 align-items-center part2">
                    <Button
                     className='rounded-circle' onClick={() => setToggleSidebar(!toggleSidebar)}>
                     <IoMdMenu / >
                    </Button>
                    <SearchBox />
                </div>
                <div className="col-lg-7 d-flex align-items-center justify-content-end part3">
                    <Button 
                    className='rounded-circle m-2'>
                   <CiLight />
                   </Button>
                   <Button 
                    className='rounded-circle m-2'>
                   <MdTextsms />
                   </Button>
                   <Button 
                    className='rounded-circle m-2'>
                   <IoNotifications />
                   </Button>
                   <div className="user d-flex align-items-center m-4">
                   <Button 
                    className='rounded-circle m-2'>
                   <FaUser />
                   </Button>
                   </div>
                </div>
                
            </div>
        </div>
    </header>
  )
}
