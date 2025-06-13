
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axios from 'axios';
import DashboardContent from './dashboard/DashboardContent';
import { FaHome } from "react-icons/fa";
import { FaChartLine } from "react-icons/fa";
import { IoSettings } from "react-icons/io5";
import DeviceDetailMenu from './layout/DeviceDetailMenu';
import { Chart } from "react-google-charts";
import './chart.css';

import DatePicker from "react-datepicker";

import "react-datepicker/dist/react-datepicker.css";





export default function DeviceDetailChart() {
    const {id}=useParams();

     const data = [
      [
        { type: "number", label: "x" },
        { type: "number", label: "values" },
        { id: "i0", type: "number", role: "interval" },
        { id: "i1", type: "number", role: "interval" },
        { id: "i2", type: "number", role: "interval" },
        { id: "i2", type: "number", role: "interval" },
        { id: "i2", type: "number", role: "interval" },
        { id: "i2", type: "number", role: "interval" },
      ],
      [1, 100, 90, 110, 85, 96, 104, 120],
      [2, 120, 95, 130, 90, 113, 124, 140],
      [3, 130, 105, 140, 100, 117, 133, 139],
      [4, 90, 85, 95, 85, 88, 92, 95],
      [5, 70, 74, 63, 67, 69, 70, 72],
      [6, 30, 39, 22, 21, 28, 34, 40],
      [7, 80, 77, 83, 70, 77, 85, 90],
      [8, 100, 90, 110, 85, 95, 102, 110],
    ];
    
     const options = {
      title: "Consommation en KWH",
      curveType: "function",
      series: [{ color: "#D9544C" }],
      intervals: { style: "bars" },
      legend: "none",
    };


    const data_curve = [
      [
        { type: "number", label: "x" },
        { type: "number", label: "values" },
        { id: "i1", type: "number", role: "interval" },
        { id: "i1", type: "number", role: "interval" },
        { id: "i1", type: "number", role: "interval" },
        { id: "i2", type: "number", role: "interval" },
        { id: "i2", type: "number", role: "interval" },
        { id: "i2", type: "number", role: "interval" },
      ],
      [1, 30, 90, 110, 85, 85, 85, 85],
      [2, 100, 17, 50, 90, 14, 124, 140],
      [3, 130, 105, 140, 100, 117, 133, 139],
      [4, 90, 85, 95, 85, 88, 92, 95],
      [5, 70, 74, 63, 67, 69, 70, 72],
      [6, 30, 39, 22, 21, 28, 34, 40],
      [7, 80, 77, 83, 70, 77, 85, 90],
      [8, 100, 90, 110, 85, 95, 102, 110],
    ];

    const options_curve = {
      title: "Current curve (H)",
      curveType: "function",
      series: [{ color: "#D9544C" }],
      intervals: { style: "bars" },
      legend: "none",
    };

      const [chartData, setChartData] = useState([]);
      const [chartData3, setChartData3] = useState([]);
      const [loading, setLoading] = useState(true);
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

useEffect(() => {
  axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_current`)
    .then((res) => {
      const result = res.data.donnees.logs || [];
      
      const formattedData = [
          [
            { type: "datetime", label: "x" }, // ou "number" si c'est un index
            { type: "number", label: "values" },
          ],
        ];
      
      let lastTimestamp = null;

      result.forEach((point) => {
        if (point && point.value !== undefined) {
          const pointTime = new Date(point.event_time).getTime();

          if (lastTimestamp === null || pointTime - lastTimestamp >= 2 * 60 * 60 * 1000) {
            formattedData.push([new Date(pointTime), point.value]);
            lastTimestamp = pointTime;
          }
        }
      });

      setChartData(formattedData);
      setLoading(false);
    })
    .catch((err) => {
      console.error("Erreur de récupération:", err);
      setLoading(false);
    });
}, []);


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

const startDatePower = new Date("2025-05-20T00:00:00").getTime();
const endDatePower = new Date("2025-05-20T23:59:59").getTime();

const [dateDebuter, setDateDebuter]=useState();

console.log('charge', selectedDate);

const [dateUse, setDateUse]=useState();
useEffect(()=>{
  setDateUse(selectedDate);

}, [])

const courbe_by_day=()=>{
  
  //const date_day = new Date();
  const now = new Date();

  // Date de début à minuit
  const dateDebut = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);

  // Date de fin à 23:59:00
  const dateFin = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 0);

  // Par exemple : les stocker dans des états
  
  //setDateFin(dateFin);

  // Ou juste les afficher dans la console

  const convertirDateDebut=dateDebut.getTime();
  console.log('dateDebut :', dateDebut.toISOString());
  console.log('dateFin   :', dateFin.toISOString());

  console.log('date convertie', convertirDateDebut);

  console.log('date valeur', dateDebut);

  // ICI c'est le reference 


  /*
  const dates = new Date(selectedDate);
  const dateDebutRef= new Date(dates.getFullYear(), dates.getMonth(), dates.getDate(), 23, 59, 0);
  setDateDebuter(dateDebutRef);

  console.log('date a referer', dateDebuter);

  console.log('dddd', selectedDate); */

  const dates = new Date(selectedDate);
  const dateDebutRef= new Date(dates.getFullYear(), dates.getMonth(), dates.getDate(), 23, 59, 0);
  setDateUse(dateDebutRef);

  console.log('date a referer', dateUse);

  console.log('dddd', selectedDate);

}

  const [startDate, setStartDate] = useState(new Date());


  const [startDateMonth, setStartDateMonth] = useState(new Date());

  const [startDateYear, setStartDateYear] = useState(new Date());


 const [voltTimeStart, setVoltTimeStart]=useState(new Date(startDate));
 const [voltTimeEnd, setVoltTimeEnd]=useState();

  const [voltTimeStartHorodatage, setVoltTimeStartHorodatage]=useState(new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 0, 0, 0).getTime());
  
  const [voltTimeEndHorodatage, setVoltTimeEndHorodatage]=useState(new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 23, 59, 0).getTime());
  
  

 useEffect(() => {
  
  console.log('startDate mis à jour :', startDate);
  console.log('volttime=', voltTimeStart);
  console.log('horo0=', voltTimeStartHorodatage);

  //const ab=startDate;
  const a1=new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 0, 0, 0);
  const a2=new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate(), 23, 59, 0);
  console.log('a1',a1);
  console.log('a2',a2);

  
}, [startDate]);




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
       {/*      <Chart
      chartType="LineChart"
      width="100%"
      height="400px"
      data={data}
      options={options}
    />

<Chart
      chartType="LineChart"
      width="100%"
      height="400px"
      data={data_curve}
      options={options_curve}
    /> */}

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
                            <Chart
            chartType="LineChart"
            width="100%"
            height="400px"
            data={chartData}
            options={options_new}
          />

          {/* ici mon input date journaliere */}
          <input className='inputDate'                
                 type="date"
                 value={selectedDate}
                 onChange={(e) => setSelectedDate(e.target.value)} />

         
        <DatePicker selected={startDate} 
        onChange={(date) =>{ setStartDate(date);
      const mydates = new Date(date); // <-- utiliser `date`, pas `startDate`
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

   setVoltTimeStart(datest); // <-- probablement tu voulais ça
   setVoltTimeStartHorodatage(datest.getTime());
   setVoltTimeEnd(datestFin);
   setVoltTimeEndHorodatage(datestFin.getTime());

    console.log("time_volt", datest);
    console.log('horodat',voltTimeStartHorodatage);



    console.log("time_voltfin", datestFin);
    console.log('horodatfin',voltTimeEndHorodatage);


//useEffect(() => {
  axios.get(`${import.meta.env.VITE_API_URL}/get_graphique_current3?end_time=${voltTimeEndHorodatage}&start_time=${voltTimeStartHorodatage}`)
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
            console.log(formattedData3);
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
                <Chart
            chartType="LineChart"
            width="100%"
            height="400px"
            data={chartData}
            options={options_new}
          />

       {/*   <input className='inputDate'                
                 type="date"
                 value={selectedDate}
                 onChange={(e) => setSelectedDate(e.target.value)} /> */}
          </>
        )}

       <div className='container-fluid'>
              <div className="row md-6">
                <div className="col-lg-12">
                  <div className='d-flex align-items-center button_date'>
                    <button className='btn rounded-circle btn_by_date_isClicked' onClick={courbe_by_day}>Jour</button> 
                    <button className='btn  rounded-circle btn_by_date_noClicked'>Mois</button> 
                    <button className='btn rounded-circle btn_by_date_noClicked'>Annee</button>

                  </div>
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
