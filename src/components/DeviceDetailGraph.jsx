import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axios from 'axios';
import DashboardContent from './dashboard/DashboardContent';
import { FaHome } from "react-icons/fa";
import { FaChartLine } from "react-icons/fa";
import { IoSettings } from "react-icons/io5";
import DeviceDetailMenu from './dashboard/DeviceDetailMenu';
import { Chart } from "react-google-charts";
import './chart.css';

import DatePicker from "react-datepicker";

import "react-datepicker/dist/react-datepicker.css";
import DeviceCommand from './DeviceCommand';

export default function DeviceDetailGraph() {

    const {id}=useParams();

      const [chartData, setChartData] = useState([]);
      const [chartData3, setChartData3] = useState([]);
      const [chartDataCurrent, setChartDataCurrent] = useState([]);
       const [chartDataPower, setChartDataPower] = useState([]);
      const [loading, setLoading] = useState(true);
       const [loadingCurrent, setLoadingCurrent] = useState(true);
       const [loadingPower, setLoadingPower] = useState(true);
      const [resultdata, setResultdata] = useState([]);

    const [selectedDate, setSelectedDate] = useState(() => {
      
    const today = new Date();
    return today.toISOString().split("T")[0]; // format 'YYYY-MM-DD'
  });

 const options_new = {
    title: "Voltage (A)",
    curveType: "function",
    legend: { position: "bottom" },
    series: [{ color: "#D9544C" }]
  };

   const options_current = {
    title: "Courant  (A)",
    curveType: "function",
    legend: { position: "bottom" },
    series: [{ color: "#D9544C" }]
  };

const options_power = {
    title: "Power (A)",
    curveType: "function",
    legend: { position: "bottom" },
    series: [{ color: "#D9544C" }]
  };



useEffect(() => {
  axios.get(`${import.meta.env.VITE_API_URL}/get_logs_name/${id}`)
    .then((res) => {
      const result = res.data.datacode;
      setResultdata(result)
      console.log(resultdata);

    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      
    });
}, []);

//test date d'aujourd'hui pour le cur power



const [dateDebuter, setDateDebuter]=useState();

console.log('charge', selectedDate);

const [dateUse, setDateUse]=useState();
useEffect(()=>{
  setDateUse(selectedDate);

}, [])



  const [startDate, setStartDate] = useState(new Date());

   const [startDateCurrent, setStartDateCurrent] = useState(new Date());
   const [startDatePower, setStartDatePower] = useState(new Date());

 const [voltTimeStartCurrent, setVoltTimeStartCurrent]=useState(new Date(startDateCurrent));
 const [voltTimeEndCurrent, setVoltTimeEndCurrent]=useState();

 const [voltTimeStartPower, setVoltTimeStartPower]=useState(new Date(startDatePower));
 const [voltTimeEndPower, setVoltTimeEndPower]=useState();



 const [voltTimeStartHorodatageCurrent, setVoltTimeStartHorodatageCurrent]=useState(new Date(startDateCurrent.getFullYear(), startDateCurrent.getMonth(), startDateCurrent.getDate(), 0, 0, 0).getTime());
  
  const [voltTimeEndHorodatageCurrent, setVoltTimeEndHorodatageCurrent]=useState(new Date(startDateCurrent.getFullYear(), startDateCurrent.getMonth(), startDateCurrent.getDate(), 23, 59, 0).getTime());
  
 const [voltTimeStartHorodatagePower, setVoltTimeStartHorodatagePower]=useState(new Date(startDatePower.getFullYear(), startDatePower.getMonth(), startDatePower.getDate(), 0, 0, 0).getTime());
  
 const [voltTimeEndHorodatagePower, setVoltTimeEndHorodatagePower]=useState(new Date(startDatePower.getFullYear(), startDatePower.getMonth(), startDatePower.getDate(), 23, 59, 0).getTime());

  const [startDateMonth, setStartDateMonth] = useState(new Date());

  const [startDateYear, setStartDateYear] = useState(new Date());

 const [voltTimeStart, setVoltTimeStart]=useState(new Date(startDate));
 const [voltTimeEnd, setVoltTimeEnd]=useState();

  const [voltTimeStartHorodatage, setVoltTimeStartHorodatage]=useState(new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 0, 0, 0).getTime());
  
  const [voltTimeEndHorodatage, setVoltTimeEndHorodatage]=useState(new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 23, 59, 0).getTime());
  
  
 useEffect(() => {
  
  console.log('startDate mis à jour :', startDate);
  console.log('volttime=', voltTimeStart);
  console.log('horo00=', voltTimeStartHorodatage);
  console.log('horo01=', voltTimeEndHorodatage);


  console.log('startDate mis à jour CURRENT:', startDateCurrent);

  //const ab=startDate;
  const a1=new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 0, 0, 0);
  const a2=new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 23, 59, 0);
  console.log('a1',a1);
  console.log('a2',a2);
  
  const jwt =localStorage.getItem('jwt');


  axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_voltage/?id=${id}&end_time=${voltTimeEndHorodatage}&start_time=${voltTimeStartHorodatage}` , {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      })
    .then((res) => {
      const result = res.data.donnees3.logs || [];
      
      const formattedData3 = [
          [
            { type: "datetime", label: "x" }, // ou "number" si c'est un index
            { type: "number", label: "values" },
          ],
        ];
      
      result.forEach((point, index) => {
        if (point && point.value !== undefined) {
          //formattedData.push([index + 1, point.value]);
          formattedData3.push([new Date(point.event_time), point.value ]);
            //console.log(formattedData3);
            
        }
      });

      setChartData3(formattedData3);
      setLoading(false);
    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      setLoading(false);
    });





  
}, [startDate]);


useEffect(() => {
  


    console.log('MYhoro0000=', voltTimeStartHorodatageCurrent);
    console.log('MYhoro0011=', voltTimeEndHorodatageCurrent);

  console.log('startDate mis à jour CURRENT:', startDateCurrent);

  //const ab=startDate;


    axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_current/?id=${id}&end_time=${voltTimeEndHorodatageCurrent}&start_time=${voltTimeStartHorodatageCurrent}`)
    .then((res) => {
      const result = res.data.donnees_current.logs || [];
      
      const formattedDataCurrent = [
          [
            { type: "datetime", label: "x" }, // ou "number" si c'est un index
            { type: "number", label: "values" },
          ],
        ];
      
      result.forEach((point, index) => {
        if (point && point.value !== undefined) {
          //formattedData.push([index + 1, point.value]);
          formattedDataCurrent.push([new Date(point.event_time), point.value ]);
            console.log(formattedDataCurrent);
            
        }
      });

      setChartDataCurrent(formattedDataCurrent);
      setLoadingCurrent(false);
    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      setLoadingCurrent(false);
    });

 





  
}, [startDateCurrent]);


useEffect(() => {
  console.log('heurepowerinit=', voltTimeStartHorodatagePower);
    console.log('heurepowerend=', voltTimeEndHorodatagePower);

  console.log('startDate mis à jour CURRENT:', startDatePower);

  const jwt =localStorage.getItem('jwt')

  //const ab=startDate;


    axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_power/?id=${id}&end_time=${voltTimeEndHorodatagePower}&start_time=${voltTimeStartHorodatagePower}` )
    .then((res) => {
      const result = res.data.donnees_power.logs || [];
      
      const formattedDataPower = [
          [
            { type: "datetime", label: "x" }, // ou "number" si c'est un index
            { type: "number", label: "values" },
          ],
        ];
      
      result.forEach((point, index) => {
        if (point && point.value !== undefined) {
          //formattedData.push([index + 1, point.value]);
          formattedDataPower.push([new Date(point.event_time), point.value ]);
            console.log(formattedDataPower);
            
        }
      });

      setChartDataPower(formattedDataPower);
      setLoadingPower(false);
    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      setLoadingPower(false);
    });

 





  
}, [startDatePower]);


  return (

        <>
      {/*  <DashboardContent /> */}
        <div className="card shadow debut border-0 p-3 mt-4">
            <center>
        <h2>Détails de l'appareil {id}</h2>
        </center>
        </div>
     <DeviceDetailMenu />
          <div className="card shadow border-0 p-3 mt-4">

           {loading ? (
          <p>Chargement...</p>
        ) : (
          <>
             <p> {new Date().toLocaleDateString()}</p> 
          {/*  <p>Date d'aujourdhi start {startDatePower}</p>
             <p>Date d'aujourdhi fin {endDatePower}</p> */}
             <div className='container-fluid'>
              <div className="row">
                <div className="col-lg-12">
                  <div className='d-flex align-items-center button_date'>
                    <button className='btn rounded-circle btn_by_date_isClicked'>Jour</button> 
                    <button className='btn  rounded-circle btn_by_date_noClicked'>Mois</button> 
                    <button className='btn rounded-circle btn_by_date_noClicked'>Annee</button>


          {/* ici mon input date journaliere */}
          <input className='inputDate'                
                 type="date"
                 value={selectedDate}
                 onChange={(e) => setSelectedDate(e.target.value)} />

         
    <DatePicker selected={startDate} 
        onChange={(date) =>{ setStartDate(date);
         const mydates = new Date(date); 
         const datest = new Date(
          mydates.getFullYear(),
          mydates.getMonth(),
         mydates.getDate(),
         0,
         0,
      0
    );
        const datestFin = new Date(
      mydates.getFullYear(),
      mydates.getMonth(),
      mydates.getDate(),
      23,
      59,
      0
    );

   setVoltTimeStart(datest); 
   setVoltTimeStartHorodatage(datest.getTime());
   setVoltTimeEnd(datestFin);
   setVoltTimeEndHorodatage(datestFin.getTime());

    console.log("time_volt", datest);
    console.log('horodat',voltTimeStartHorodatage);

    console.log("time_voltfin", datestFin);
    console.log('horodatfin',voltTimeEndHorodatage);


//useEffect(() => {
  axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_voltage/?id=${id}&end_time=${voltTimeEndHorodatage}&start_time=${voltTimeStartHorodatage}`)
    .then((res) => {
      const result = res.data.donnees3.logs || [];
      
      const formattedData3 = [
          [
            { type: "datetime", label: "x" }, // ou "number" si c'est un index
            { type: "number", label: "values" },
          ],
        ];
      
      result.forEach((point, index) => {
        if (point && point.value !== undefined) {
          //formattedData.push([index + 1, point.value]);
          formattedData3.push([new Date(point.event_time), point.value ]);
            //console.log(formattedData3);
            //alert(formattedData3);
        }
      });

      setChartData3(formattedData3);
      setLoading(false);
    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      setLoading(false);
    });
//}, []);

  
             
         }} />

    <DatePicker
      selected={startDateMonth}
      onChange={(date) => setStartDateMonth(date)}
      dateFormat="MM/yyyy"
      excludeDates={[new Date("2024-05-01"), new Date("2024-06-01")]}
      showMonthYearPicker
    />

          <DatePicker
        selected={startDateYear}
        onChange={(date) =>{ setStartDateYear(date);
          console.log('annee', startDateYear);
         }}
        selectsStart
        startDate={startDateYear}
        
        dateFormat="yyyy"
        showYearPicker
       
      />

                </div>
                </div>
              </div>
             </div>
           <Chart
            chartType="LineChart"
            width="100%"
            height="400px"
            data={chartData3}
            options={options_new}
          />     

          </>
        )}

        <div className='container-fluid'>
            <div className="row">
                <div className="col-lg-12">
        <DatePicker selected={startDateCurrent} 
        onChange={(dateCurrent) =>{ setStartDateCurrent(dateCurrent);
         const mydatesCurrent = new Date(dateCurrent); 
         const datestCurrent = new Date(
          mydatesCurrent.getFullYear(),
          mydatesCurrent.getMonth(),
         mydatesCurrent.getDate(),
         0,
         0,
      0
    );
    const datestFinCurrent = new Date(
      mydatesCurrent.getFullYear(),
      mydatesCurrent.getMonth(),
      mydatesCurrent.getDate(),
      23,
      59,
      0
    );

   setVoltTimeStartCurrent(datestCurrent); 
   setVoltTimeStartHorodatageCurrent(datestCurrent.getTime());
   setVoltTimeEndCurrent(datestFinCurrent);
   setVoltTimeEndHorodatageCurrent(datestFinCurrent.getTime());

    console.log("time_volt", datestCurrent);
    console.log('horodat',voltTimeStartHorodatageCurrent);

    console.log("time_voltfin", datestFinCurrent);
    console.log('horodatfin',voltTimeEndHorodatageCurrent);


//useEffect(() => {
  axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_current/?id=${id}&end_time=${voltTimeEndHorodatageCurrent}&start_time=${voltTimeStartHorodatageCurrent}`)
    .then((res) => {
      const result = res.data.donnees_current.logs || [];
      
      const formattedDataCurrent = [
          [
            { type: "datetime", label: "x" }, // ou "number" si c'est un index
            { type: "number", label: "values" },
          ],
        ];
      
      result.forEach((point, index) => {
        if (point && point.value !== undefined) {
          //formattedData.push([index + 1, point.value]);
          formattedDataCurrent.push([new Date(point.event_time), point.value ]);
           // console.log(formattedDataCurrent);
           
        }
      });

      setChartDataCurrent(formattedDataCurrent);
      setLoadingCurrent(false);
    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      setLoadingCurrent(false);
    });
//}, []);

  
             
         }} />


        <Chart
            chartType="LineChart"
            width="100%"
            height="400px"
            data={chartDataCurrent}
            options={options_current}
          />     

                </div>
            </div>
        </div>


           <div className='container-fluid'>
            <div className="row">
                <div className="col-lg-12">
        <DatePicker selected={startDatePower} 
        onChange={(datePower) =>{ setStartDatePower(datePower);
         const mydatesCurrent = new Date(datePower); 
         const datestCurrent = new Date(
          mydatesCurrent.getFullYear(),
          mydatesCurrent.getMonth(),
         mydatesCurrent.getDate(),
         0,
         0,
      0
    );
    const datestFinCurrent = new Date(
      mydatesCurrent.getFullYear(),
      mydatesCurrent.getMonth(),
      mydatesCurrent.getDate(),
      23,
      59,
      0
    );

   setVoltTimeStartPower(datestCurrent); 
   setVoltTimeStartHorodatagePower(datestCurrent.getTime());
   setVoltTimeEndPower(datestFinCurrent);
   setVoltTimeEndHorodatagePower(datestFinCurrent.getTime());

    console.log("time_volt", datestCurrent);
    console.log('horodat',voltTimeStartHorodatagePower);

    console.log("time_voltfin", datestFinCurrent);
    console.log('horodatfin',voltTimeEndHorodatagePower);


//useEffect(() => {
  axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_power/?id=${id}&end_time=${voltTimeEndHorodatagePower}&start_time=${voltTimeStartHorodatagePower}`)
    .then((res) => {
      const result = res.data.donnees_power.logs || [];
      
      const formattedDataPower = [
          [
            { type: "datetime", label: "x" }, // ou "number" si c'est un index
            { type: "number", label: "values" },
          ],
        ];
      
      result.forEach((point, index) => {
        if (point && point.value !== undefined) {
          //formattedData.push([index + 1, point.value]);
          formattedDataPower.push([new Date(point.event_time), point.value ]);
           // console.log(formattedDataCurrent);
           
        }
      });

      setChartDataPower(formattedDataPower);
      setLoadingPower(false);
    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      setLoadingPower(false);
    });
//}, []);

  
             
         }} />


        <Chart
            chartType="LineChart"
            width="100%"
            height="400px"
            data={chartDataPower}
            options={options_power}
          />     

                </div>
            </div>
        </div>     

       <div className='container-fluid'>
              <div className="row md-6">
                <div className="col-lg-12">
                  <div className='d-flex align-items-center button_date'>
                    <button className='btn rounded-circle btn_by_date_isClicked'>Jour</button> 
                    <button className='btn  rounded-circle btn_by_date_noClicked'>Mois</button> 
                    <button className='btn rounded-circle btn_by_date_noClicked'>Annee</button>

                  </div>
                </div>
              </div>
             </div>
             <div className="container-fluid">
                <div className="row">
                    <div className="col-lg-12">
                    <DeviceCommand />
                    </div>
                </div>
             </div>
           <ul>
             {resultdata.map((item)=>(
              <li key={item.code}>
                {item.code}
              </li>

             ))}
             </ul>

          </div>
          </>
  )
}

