
import React, {useEffect, useState,useContext} from 'react'
import { FaHome } from "react-icons/fa";
import { FaChartLine } from "react-icons/fa";
import { IoSettings } from "react-icons/io5";
import { Link, useParams } from 'react-router-dom';
import { MyContext } from '../../App';


export default function DeviceDetailMenu() {
     // const[isClick, setIsClick]=useState(1);
     const context=useContext(MyContext);
    
        const {id}=useParams();
  return (
    <div className="card shadow menu border-0 p-3">
    <div className='row'>
      
        
        <div className='col-lg-3'>
            <div className={`${context.isClick===1 ? 'menu_active' : 'menu_noactive' }`} >
            <Link onClick={()=>context.setIsClick(1)} className={`${context.isClick===1 ? 'menu_link_active' : 'menu_link_noactive' }`} to={`/device/${id}`} > <FaHome /> <span > Accueil </span> </Link>
            </div>
        </div>
        <div className='col-lg-3'>
        <div className={`${context.isClick===2 ? 'menu_active' : 'menu_noactive' }`}>
            <Link onClick={()=>context.setIsClick(2)} className={`${context.isClick===2 ? 'menu_link_active' : 'menu_link_noactive' }`} to={`/appareils_chart/${id}`} > <FaChartLine /><span >  Chart </span> </Link>
            </div>
        </div>
        <div className='col-lg-3'>
        <div className='menu_noactive'>
            <Link className='menu_link_noactive' to={('/')} > <IoSettings />  Parametres </Link>
            </div>
        </div>
        <div className='col-lg-3'>
        <div className='menu_noactive'>
            <Link className='menu_link_noactive' to={('/')} > <IoSettings />  Cost </Link>
            </div>
        </div>
        
     
    
    </div>
    </div>
  )
}
