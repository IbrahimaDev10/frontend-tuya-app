import React, { useState, useContext, useEffect } from 'react'
import auchan from "../../assets/images/myauchan.png";
import DashboardBox from '../DashboardBox'
import { FaCircleUser } from 'react-icons/fa6'
import { IoMdCart } from 'react-icons/io'
import { MdShoppingBag } from 'react-icons/md'
import { GiStarsStack } from 'react-icons/gi'

import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import { Chart } from "react-google-charts";
import { MyContext } from '../../App';



export default function DashboardContent() {
  
    const data = [
        ["Task", "Hours per Day"],
        ["Work", 9],
        ["Eat", 2],
        ["Commute", 2],
        ["Watch TV", 2],
        ["Sleep", 7],
      ];
    
      const options = {
        title: "My Daily Activities",
        backgroundColor:'transparent',
        
        legendTextStyle:{color:'#fff'},
        titleTextStyle:{color:'#fff'},
        chartArea: { width: "100%", height: "100%" },
      };

    const [voltage, setVoltage]=useState('voltage');

      const [showBy, setShowBy] = useState('a');
      const [showByCategories, setShowByCategories] = useState('q');
     

      const { setIsHideSidebarAndHeader } = useContext(MyContext);

      useEffect(() => {
        setIsHideSidebarAndHeader(true); // Remet à false dès que la page est chargée
        
      }, []);
     
  return (
  
    <div className="container-fluid right-content w-100 ">
        <div className="row dashboardBoxWrapperRow ">
        <div className="col-lg-9">
        <div className="dashboardBoxWrapper d-flex">
        <DashboardBox color={["#00A2E8","#fff"]} titre='Materiels' icon={<FaCircleUser />} />
        <DashboardBox color={["#00A2E8","#fff"]} titre='Total Materiels' icon={<IoMdCart />} />
        <DashboardBox color={["#00A2E8","#fff"]} titre='Total Consommation' icon={<MdShoppingBag />} />
        <DashboardBox color={["#00A2E8","#fff"]} titre='Divers' icon={<GiStarsStack />}  />
        </div>
        </div>
        <div className="col-lg-3 pl-0">
         <div className="box graphBox">
           <div className='contentbox'>
            <div>
            <img className='logo_auchan' src={auchan}  />
            </div>
            <div className='textBox'>
              <p className='textBoxParagraph'>
                Partenaire officiel Lorem ipsum, dolor sit amet consectetur 
                adipisicing elit. Ipsam necessitatibus laborum maxime ducimus molestias vel nulla autem
                  
              </p>
            </div>
            </div>
            </div>
            </div>

         </div>
   

 
        </div>

   
 
  )
}
