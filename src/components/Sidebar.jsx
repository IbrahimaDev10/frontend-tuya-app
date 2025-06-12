import React from 'react'
import { Button } from '@mui/material'
import { Link } from 'react-router-dom'
import { MdDashboard } from "react-icons/md";
import { FaAngleDown } from "react-icons/fa";
import { FaLandmark } from "react-icons/fa";
import { MdElectricalServices } from "react-icons/md";
import { IoMdNotifications } from "react-icons/io";
import { BiSolidMessageSquareDetail } from "react-icons/bi";
import { useQuery, useQueries } from '@tanstack/react-query';
import { MyContext } from '../App';
import { useEffect, useState } from 'react'
import axios from 'axios';
import Logout from '../components/auth/Logout/Logout';

import '../sidebar.css'

export default function Sidebar() {

  const id='bfaac3ac13dc9aaa2daza6';
  

    {/*
    const fetchSpaceList = async () => {
        const response = await axios.get("http://localhost:5000/space-list");
        return response.data;
      };

      const { data: spaceListData, isLoading, error } = useQuery({
        queryKey: ['space-list'],
        queryFn: fetchSpaceList,
        //refetchInterval: 3000,
       
      });

     
      const list = spaceListData?.spaces?.data || [];

      const assetQueries = useQueries({
        queries: list.map(id => ({
          queryKey: ['asset-name', id],
          queryFn: async () => {
            const response = await axios.get(`http://localhost:5000/asset-name/${id}`);
            return response.data;
          },
        })),
      }); */}

   // const list = data.spaces[0].data ;



  return (
    <div className='sidebar'>
        <ul>
            <li>
                <Link to='/'>
                <Button className='w-100'>
                    <span className='icon'> 
                     <MdDashboard />
                    </span>
                    Dashboard
                    <span className='icon-right'></span>
                </Button>
                </Link>
            </li>
            <li>
                <Link to='/'>
                <Button className='w-100'>
                    <span className='icon'> 
                     <FaLandmark />
                    </span>
                    Clients
                    <span className='icon-right'><FaAngleDown /></span>
                    
                </Button>
     
                </Link>
            </li>

            <li>
                <Link to='/appareils'>
                <Button className='w-100'>
                    <span className='icon'> 
                     <MdElectricalServices />
                    </span>
                   Appareils
                    <span className='icon-right'><FaAngleDown /></span>
                </Button>
                </Link>
            </li>
            <li>
                <Link to={`/devicesocket/${id}`}>
                <Button className='w-100'>
                    <span className='icon'> 
                     <IoMdNotifications />
                    </span>
                 socket
                    <span className='icon-right'><FaAngleDown /></span>
                </Button>
                </Link>
            </li>
            <li>
                <Link to='/'>
                <Button className='w-100'>
                    <span className='icon'> 
                     <BiSolidMessageSquareDetail />
                    </span>
                   Messages
                    <span className='icon-right'><FaAngleDown /></span>
                </Button>
                </Link>
                <Logout />
            </li>
        </ul>
      {/*  <ul >
            {list.map((item, index) => (
              <li key={index}><h3>Espace ID : {item}</h3></li>
            ))} 
          </ul> */}

    {/*
{assetQueries.map((query, index) => {
              if (query.isLoading) return <li key={index}>Chargement...</li>;
              if (query.error) return <li key={index}>Erreur</li>;
              return (
                <li key={index}>
                  <Link to={`/clients/${list[index]}`}>{query.data?.asset[0]?.asset_full_name || `Client ${list[index]}`}</Link>
                </li>
              );
            })} 
            </ul> */}

    </div>
  )
}
