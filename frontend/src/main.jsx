import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

const API="http://localhost:8000/api";
const demo=[["admin@example.com","admin123"],["manager@example.com","manager123"],["employee@example.com","employee123"]];

async function request(path, options={}) {
  const token=localStorage.getItem("token");
  const headers={"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`}:{})};
  const r=await fetch(API+path,{...options,headers});
  if(!r.ok) throw new Error((await r.json()).detail||"Request failed");
  return r.json();
}

function Login({onLogin}) {
  const [email,setEmail]=useState(demo[1][0]),[password,setPassword]=useState(demo[1][1]),[error,setError]=useState("");
  async function submit(e){e.preventDefault();try{const x=await request("/auth/login",{method:"POST",body:JSON.stringify({email,password})});localStorage.setItem("token",x.access_token);onLogin(x.user)}catch(e){setError(e.message)}}
  return <main className="login"><form onSubmit={submit}><h1>AI Enterprise</h1><p>Sign in to the management platform.</p><input value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email"/><input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password"/><button>Sign in</button><small>Demo: manager@example.com / manager123</small>{error&&<b>{error}</b>}</form></main>
}

function App({user,onLogout}) {
  const [tab,setTab]=useState("Dashboard"),[data,setData]=useState([]),[question,setQuestion]=useState("Which projects have the most unfinished tasks?"),[answer,setAnswer]=useState("");
  const tabs=["Dashboard","Projects","Tasks","Employees","AI Copilot"];
  async function load(){if(tab==="Dashboard")return;const path={"/Projects":"/projects","/Tasks":"/tasks","/Employees":"/employees"}[tab];if(path)setData(await request(path))}
  useEffect(()=>{load().catch(()=>{})},[tab]);
  async function ask(){setAnswer("Thinking...");try{setAnswer((await request("/copilot",{method:"POST",body:JSON.stringify({question})})).answer)}catch(e){setAnswer(e.message)}}
  async function addTask(){if(user.role==="employee")return alert("Employees cannot create tasks.");const x=await request("/tasks",{method:"POST",body:JSON.stringify({title:"New task",status:"todo",priority:"medium",project_id:1,assignee_id:3})});setData([...data,x])}
  return <div><header><strong>AI Enterprise Management</strong><span>{user.name} · {user.role}</span><button onClick={onLogout}>Logout</button></header><nav>{tabs.map(x=><button className={tab===x?"active":""} onClick={()=>setTab(x)}>{x}</button>)}</nav><main className="content">{tab==="Dashboard"&&<><h1>Operations Dashboard</h1><div className="cards"><div>Role<strong>{user.role}</strong></div><div>AI Copilot<strong>Ready</strong></div><div>API<strong>FastAPI</strong></div></div><p>Use the navigation to inspect enterprise data and ask the AI copilot operational questions.</p></>}{["Projects","Tasks","Employees"].includes(tab)&&<><h1>{tab}</h1>{tab==="Tasks"&&user.role!=="employee"&&<button onClick={addTask}>Add demo task</button>}<div className="list">{data.map(x=><article><strong>{x.name||x.title}</strong><span>{x.status||x.role||x.priority}</span><small>{x.description||x.email||`Project ${x.project_id||""}`}</small></article>)}</div></>}{tab==="AI Copilot"&&<><h1>AI Copilot</h1><p>Ask questions about current projects, tasks and employees.</p><textarea value={question} onChange={e=>setQuestion(e.target.value)}/><button onClick={ask}>Ask Copilot</button>{answer&&<pre>{answer}</pre>}</>}</main></div>
}

function Root(){const [user,setUser]=useState(null);useEffect(()=>{if(localStorage.getItem("token"))request("/auth/me").then(setUser).catch(()=>localStorage.removeItem("token"))},[]);if(!user)return <Login onLogin={setUser}/>;return <App user={user} onLogout={()=>{localStorage.removeItem("token");setUser(null)}}/>}
createRoot(document.getElementById("root")).render(<Root/>);
