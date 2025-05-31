import React from 'react'
import { FaCircleUser } from "react-icons/fa6";
import TrendingUpIcon from '@mui/icons-material/TrendingUp';



import { Chart } from "react-google-charts";



export default function DashboardBox(props) {


  return (
    
    <div className="dashboardBox" style={{backgroundImage:`linear-gradient( ${props.color[0]}, ${props.color[1]})`}}>
        <span className='chart'><TrendingUpIcon /></span>
        <div className="d-flex w-100">
            <div className="col1">
                <h4 className='text-white'>
                    {props.titre ?
                     props.titre ? props.titre : ''
                     : ''
                    }
                </h4>
                <span className='text-bg'>314</span>
            </div>
            <div className="element">

                {
                    props.icon ?
                <span className='icon'>
                   {props.icon ? props.icon : ''}
                </span>
                 : ''
                }

                {/*
                <span className='icon'>
                    <FaCircleUser />
                </span>  */}
            </div>
            </div>
            <div className='element_bas'>
                  
            </div>
        

    </div>
   
  
  )
}
