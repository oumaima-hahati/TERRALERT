import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MapContainer, TileLayer, GeoJSON} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './style.css';

function formatValue(value, decimals = 2, unit = '') {
  if (value === null || value === undefined || value === '') {
    return 'Not available';
  }
  const n = Number(value);
  return Number.isFinite(n)
    ? n.toLocaleString('en-US', {
        maximumFractionDigits: decimals
      }) + unit
    : 'Not available';
}

function popupContent(title, rows) {
  const container = document.createElement('div');
  container.style.minWidth = '240px';

  const heading = document.createElement('h3');
  heading.textContent = title;
  heading.style.marginBottom = '12px';
  container.appendChild(heading);

  rows.forEach(([label, value]) => {
    const line = document.createElement('div');
    line.style.marginBottom = '6px';

    const strong = document.createElement('strong');
    strong.textContent = label + ': ';
    line.appendChild(strong);
    line.appendChild(document.createTextNode(String(value)));

    container.appendChild(line);
  });

  return container;
}

function communePopup(props) {
  return popupContent(props.commune_name || 'Commune', [
    ['Population', formatValue(props.population, 0)],
    ['Area', formatValue(props.area, 2, ' km²')],
    ['Population density', formatValue(props.population_density, 2, ' /km²')],
    ['Average elevation', formatValue(props.avg_elevation, 2, ' m')],
    ['Average slope', formatValue(props.avg_slope, 2, '°')],
    ['River network', formatValue(props.river_length, 2, ' km')],
    ['Drainage density', formatValue(props.drainage_density, 3, ' km/km²')],
    ['Urban coverage', formatValue(props.urban_coverage, 2, '%')],
    ['Tree coverage', formatValue(props.tree_coverage, 2, '%')],
    ['Vegetation coverage', formatValue(props.vegetation_coverage, 2, '%')],
    ['Hazard assessment', 'Pending validation']
  ]);
}

function riverPopup(props) {
  const rows = [
    ['Length', formatValue(props.length_km, 3, ' km')]
  ];

  if (props.fclass?.trim())
    rows.push(['Classification', props.fclass]);

  if (props.stream_type?.trim())
    rows.push(['Stream type', props.stream_type]);

  if (props.osm_id)
    rows.push(['OSM ID', props.osm_id]);

  return popupContent(
    props.name?.trim() || 'River segment',
    rows
  );
}

function App(){
  const [geo,setGeo]=useState(null),[error,setError]=useState('');
  const [rivers,setRivers]=useState(null);
  const [showRivers,setShowRivers]=useState(true);
  const [riversError,setRiversError]=useState('');
  useEffect(()=>{fetch('/api/flood/indicators').then(async r=>{if(!r.ok)throw Error((await r.json()).detail||'Cannot load communes');return r.json()}).then(setGeo).catch(e=>setError(e.message))},[]);
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
          layer.bindPopup(riverPopup(props));
        }}
      />}
      {geo&&<GeoJSON data={geo} style={{color:'#0e7490',weight:2,fillOpacity:.12}} onEachFeature={(feature,layer)=>layer.bindPopup(communePopup(feature.properties || {}))}/>}</MapContainer></section>
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