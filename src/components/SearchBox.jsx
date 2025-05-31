import React from 'react'
import { FaSearch } from "react-icons/fa";

export default function SearchBox() {
  return (
    <div className='searchbox position-relative d-flex align-items-center m-2'>
        <FaSearch className='iconSearch m-2' />
        <input type='text' placeholder='recherche...' />
        </div>
  )
}
