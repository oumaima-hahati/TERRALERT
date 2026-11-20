import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MapContainer, TileLayer, GeoJSON} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './style.css';
function App(){
  const [geo,setGeo]=useState(null),[error,setError]=useState('');
  useEffect(()=>{fetch('/api/communes').then(async r=>{if(!r.ok)throw Error((await r.json()).detail||'Cannot load communes');return r.json()}).then(setGeo).catch(e=>setError(e.message))},[]);
  return <main><header><h1>TERRALERT</h1><p>Multi-hazard GIS and early-warning platform — prototype</p></header>
    <section><h2>Study area</h2>{error&&<p className="notice">{error}</p>}<MapContainer center={[35.73,-5.83]} zoom={10} style={{height:'65vh',width:'100%'}}><TileLayer attribution='&copy; OpenStreetMap contributors' url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'/>{geo&&<GeoJSON data={geo} style={{color:'#0e7490',weight:2,fillOpacity:.12}} onEachFeature={(feature,layer)=>layer.bindPopup(String(feature.properties?.name||feature.properties?.nom||'Commune'))}/>}</MapContainer></section>
    <footer>Risk outputs require validated datasets and models. No operational alerts are provided.</footer></main>
}
createRoot(document.getElementById('root')).render(<App/>);
fetch("http://localhost:8000/api/health")
  .then((response) => response.json())
  .then((data) => {
    console.log("TERRALERT backend:", data);
  })
  .catch((error) => {
    console.error("Backend connection failed:", error);
  });