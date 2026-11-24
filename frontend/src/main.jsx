import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MapContainer, TileLayer, GeoJSON} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './style.css';
function App(){
  const [geo,setGeo]=useState(null),[error,setError]=useState('');
  const [rivers,setRivers]=useState(null);
  const [showRivers,setShowRivers]=useState(true);
  const [riversError,setRiversError]=useState('');
  useEffect(()=>{fetch('/api/communes').then(async r=>{if(!r.ok)throw Error((await r.json()).detail||'Cannot load communes');return r.json()}).then(setGeo).catch(e=>setError(e.message))},[]);
  useEffect(()=>{
    fetch('/api/rivers')
      .then(async r=>{
        if(!r.ok) throw Error('Cannot load rivers');
        return r.json();
      })
      .then(setRivers)
      .catch(e=>setRiversError(e.message));
  },[]);
  return <main><header><h1>TERRALERT</h1><p>Multi-hazard GIS and early-warning platform — prototype</p></header>
    <section><h2>Study area</h2>
    <label style={{display:'block',marginBottom:'12px'}}>
      <input
        type="checkbox"
        checked={showRivers}
        onChange={e=>setShowRivers(e.target.checked)}
      />
      Show rivers
    </label>
    {riversError&&<p className="notice">{riversError}</p>}{error&&<p className="notice">{error}</p>}<MapContainer center={[35.73,-5.83]} zoom={10} style={{height:'65vh',width:'100%'}}><TileLayer attribution='&copy; OpenStreetMap contributors' url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'/>{showRivers&&rivers&&
      <GeoJSON
        data={rivers}
        style={{color:'#2563eb',weight:2.5,opacity:0.9}}
        onEachFeature={(feature,layer)=>{
          const props=feature.properties||{};
          layer.bindPopup(
            'River segment' +
            '<br>Length: '+(props.length_km??'N/A')+' km' +
            '<br>Average discharge: '+(props.dis_av_cms??'N/A')+' m³/s'
          );
        }}
      />}
      {geo&&<GeoJSON data={geo} style={{color:'#0e7490',weight:2,fillOpacity:.12}} onEachFeature={(feature,layer)=>layer.bindPopup(String(feature.properties?.nom_fr||feature.properties?.name||feature.properties?.nom||'Commune'))}/>}</MapContainer></section>
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