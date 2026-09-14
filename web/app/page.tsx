'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

type Doc = {
  id:string; file_name:string; storage_path:string; document_name:string|null; document_type:string;
  owner_name:string|null; reference_number:string|null; issue_date:string|null; expiry_date:string|null;
  notes:string|null; mime_type:string|null; extraction_status:string; created_at:string
}
type EventRow = { id:string; title:string; description:string|null; event_date:string; reminder_days:number[]; created_at:string }

const TYPES=['Passport','Visa','Insurance','Contract','Lease','Bank Document','Investment Document','License','Certificate','Personal Document','Other']

function daysUntil(value:string|null){ if(!value) return null; const a=new Date(); a.setHours(0,0,0,0); const b=new Date(value+'T00:00:00'); return Math.ceil((b.getTime()-a.getTime())/86400000) }

export default function Home(){
  const [session,setSession]=useState<Session|null>(null)
  const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [authMode,setAuthMode]=useState<'signin'|'signup'>('signin')
  const [docs,setDocs]=useState<Doc[]>([]); const [events,setEvents]=useState<EventRow[]>([]); const [tab,setTab]=useState<'dashboard'|'documents'|'events'>('dashboard')
  const [search,setSearch]=useState(''); const [busy,setBusy]=useState(false); const [message,setMessage]=useState(''); const [error,setError]=useState('')
  const [showUpload,setShowUpload]=useState(false); const [showEvent,setShowEvent]=useState(false)
  const [file,setFile]=useState<File|null>(null); const [name,setName]=useState(''); const [type,setType]=useState('Other'); const [expiry,setExpiry]=useState(''); const [owner,setOwner]=useState(''); const [ref,setRef]=useState(''); const [notes,setNotes]=useState('')
  const [eventTitle,setEventTitle]=useState(''); const [eventDate,setEventDate]=useState(''); const [eventDescription,setEventDescription]=useState('')

  useEffect(()=>{ supabase.auth.getSession().then(({data})=>setSession(data.session)); const {data:{subscription}}=supabase.auth.onAuthStateChange((_e,s)=>setSession(s)); return()=>subscription.unsubscribe() },[])
  useEffect(()=>{ if(session){ loadAll() } else { setDocs([]); setEvents([]) } },[session])

  async function loadAll(){
    const [{data:d,error:de},{data:e,error:ee}]=await Promise.all([
      supabase.from('documents').select('*').order('created_at',{ascending:false}),
      supabase.from('events').select('*').order('event_date',{ascending:true})
    ])
    if(de||ee) setError(de?.message||ee?.message||'Failed to load data'); else {setDocs((d||[]) as Doc[]);setEvents((e||[]) as EventRow[])}
  }

  async function authSubmit(e:FormEvent){
    e.preventDefault(); setBusy(true); setError(''); setMessage('')
    const result=authMode==='signin' ? await supabase.auth.signInWithPassword({email,password}) : await supabase.auth.signUp({email,password})
    if(result.error) setError(result.error.message); else if(authMode==='signup' && !result.data.session) setMessage('Account created. Check your email to confirm it, then sign in.')
    setBusy(false)
  }

  async function uploadDocument(e:FormEvent){
    e.preventDefault(); if(!session?.user||!file) return; setBusy(true); setError(''); setMessage('')
    try{
      const safe=file.name.replace(/[^a-zA-Z0-9._-]/g,'_'); const path=`${session.user.id}/${crypto.randomUUID()}-${safe}`
      const {error:upErr}=await supabase.storage.from('documents').upload(path,file,{contentType:file.type||'application/octet-stream',upsert:false})
      if(upErr) throw upErr
      const {error:dbErr}=await supabase.from('documents').insert({user_id:session.user.id,file_name:file.name,storage_path:path,document_name:name||file.name.replace(/\.[^.]+$/,''),document_type:type,owner_name:owner||null,reference_number:ref||null,expiry_date:expiry||null,notes:notes||null,mime_type:file.type||null,extraction_status:'stored'})
      if(dbErr){ await supabase.storage.from('documents').remove([path]); throw dbErr }
      setShowUpload(false); setFile(null);setName('');setType('Other');setExpiry('');setOwner('');setRef('');setNotes(''); setMessage('Document uploaded securely.'); await loadAll()
    }catch(err:any){setError(err?.message||'Upload failed')} finally{setBusy(false)}
  }

  async function downloadDocument(doc:Doc){
    setError(''); const {data,error}=await supabase.storage.from('documents').download(doc.storage_path); if(error){setError(error.message);return}
    const url=URL.createObjectURL(data); const a=document.createElement('a'); a.href=url;a.download=doc.file_name;a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000)
  }

  async function deleteDocument(doc:Doc){
    if(!confirm(`Delete ${doc.document_name||doc.file_name}?`)) return
    setBusy(true); const {error:se}=await supabase.storage.from('documents').remove([doc.storage_path]); const {error:de}=await supabase.from('documents').delete().eq('id',doc.id)
    if(se||de) setError(se?.message||de?.message||'Delete failed'); else await loadAll(); setBusy(false)
  }

  async function addEvent(e:FormEvent){
    e.preventDefault(); if(!session?.user) return; setBusy(true); setError('')
    const {error}=await supabase.from('events').insert({user_id:session.user.id,title:eventTitle,event_date:eventDate,description:eventDescription||null,reminder_days:[7,3,1]})
    if(error)setError(error.message);else{setEventTitle('');setEventDate('');setEventDescription('');setShowEvent(false);await loadAll()} setBusy(false)
  }
  async function deleteEvent(id:string){ if(!confirm('Delete this event?'))return; const {error}=await supabase.from('events').delete().eq('id',id); if(error)setError(error.message);else await loadAll() }

  const filtered=useMemo(()=>{const q=search.toLowerCase().trim(); if(!q)return docs; return docs.filter(d=>[d.document_name,d.file_name,d.document_type,d.owner_name,d.reference_number,d.notes].some(v=>(v||'').toLowerCase().includes(q)))},[docs,search])
  const exp7=docs.filter(d=>{const n=daysUntil(d.expiry_date);return n!==null&&n>=0&&n<=7}).length
  const exp30=docs.filter(d=>{const n=daysUntil(d.expiry_date);return n!==null&&n>=0&&n<=30}).length
  const exp90=docs.filter(d=>{const n=daysUntil(d.expiry_date);return n!==null&&n>=0&&n<=90}).length
  const upcoming=events.filter(e=>daysUntil(e.event_date)!==null && (daysUntil(e.event_date) as number)>=0).slice(0,5)

  if(!session) return <main className="shell"><div className="auth card"><div className="brand"><div className="logo">D</div><div><h1>Documenty</h1><div className="muted">Private personal document vault</div></div></div><p className="muted">Your documents and metadata are protected by Supabase authentication and row-level security.</p>{error&&<div className="error">{error}</div>}{message&&<div className="success">{message}</div>}<form onSubmit={authSubmit}><div className="field"><label>Email</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></div><div className="field"><label>Password</label><input type="password" minLength={8} value={password} onChange={e=>setPassword(e.target.value)} required/></div><button className="btn" disabled={busy}>{busy?'Please wait...':authMode==='signin'?'Sign in':'Create account'}</button><button type="button" className="btn ghost" style={{marginLeft:8}} onClick={()=>{setAuthMode(authMode==='signin'?'signup':'signin');setError('');setMessage('')}}>{authMode==='signin'?'First time? Create account':'Already registered? Sign in'}</button></form></div></main>

  return <main className="shell">
    <div className="topbar"><div className="brand"><div className="logo">D</div><div><h1>Documenty</h1><div className="muted">Secure cloud vault</div></div></div><div className="actions"><span className="muted" style={{alignSelf:'center'}}>{session.user.email}</span><button className="btn secondary" onClick={()=>supabase.auth.signOut()}>Sign out</button></div></div>
    {error&&<div className="error">{error}</div>}{message&&<div className="success">{message}</div>}
    <div className="tabs"><button className={`tab ${tab==='dashboard'?'active':''}`} onClick={()=>setTab('dashboard')}>Dashboard</button><button className={`tab ${tab==='documents'?'active':''}`} onClick={()=>setTab('documents')}>Documents</button><button className={`tab ${tab==='events'?'active':''}`} onClick={()=>setTab('events')}>Events</button></div>

    {tab==='dashboard'&&<><div className="grid"><div className="card stat"><span className="muted">Documents</span><strong>{docs.length}</strong></div><div className="card stat"><span className="muted">Expiring in 7 days</span><strong>{exp7}</strong></div><div className="card stat"><span className="muted">Expiring in 30 days</span><strong>{exp30}</strong></div><div className="card stat"><span className="muted">Expiring in 90 days</span><strong>{exp90}</strong></div></div><div className="section-title" style={{marginTop:22}}><h2>Upcoming</h2><button className="btn" onClick={()=>setShowEvent(true)}>Add event</button></div><div className="card">{upcoming.length?upcoming.map(e=><div key={e.id} className="doc" style={{padding:'10px 0'}}><div><strong>{e.title}</strong><div className="meta">{e.event_date} · {daysUntil(e.event_date)} days</div></div></div>):<div className="empty">No upcoming events.</div>}</div></>}

    {tab==='documents'&&<><div className="section-title"><h2>Documents</h2><button className="btn" onClick={()=>setShowUpload(true)}>Upload document</button></div><div className="toolbar"><input className="search" placeholder="Search documents, owner, reference or notes..." value={search} onChange={e=>setSearch(e.target.value)}/></div><div className="docs">{filtered.map(d=><div className="card doc" key={d.id}><div><h3>{d.document_name||d.file_name}</h3><div><span className="pill">{d.document_type}</span>{d.expiry_date&&<span className="pill">Expires {d.expiry_date}</span>}</div><div className="meta">{d.owner_name&&<>Owner: {d.owner_name}<br/></>}{d.reference_number&&<>Ref: {d.reference_number}<br/></>}Uploaded {new Date(d.created_at).toLocaleDateString()}</div></div><div className="actions"><button className="btn secondary" onClick={()=>downloadDocument(d)}>Download</button><button className="btn danger" disabled={busy} onClick={()=>deleteDocument(d)}>Delete</button></div></div>)}{!filtered.length&&<div className="card empty">No documents found.</div>}</div></>}

    {tab==='events'&&<><div className="section-title"><h2>Events & reminders</h2><button className="btn" onClick={()=>setShowEvent(true)}>Add event</button></div><div className="docs">{events.map(e=><div className="card doc" key={e.id}><div><h3>{e.title}</h3><div className="meta">{e.event_date} · {daysUntil(e.event_date)} days<br/>{e.description}</div></div><button className="btn danger" onClick={()=>deleteEvent(e.id)}>Delete</button></div>)}{!events.length&&<div className="card empty">No events yet.</div>}</div></>}

    {showUpload&&<div className="modal" onMouseDown={e=>{if(e.target===e.currentTarget)setShowUpload(false)}}><form className="card" onSubmit={uploadDocument}><div className="section-title"><h2>Upload document</h2><button type="button" className="btn ghost" onClick={()=>setShowUpload(false)}>Close</button></div><div className="field"><label>File</label><input type="file" accept=".pdf,.docx,.xlsx,.jpg,.jpeg,.png" onChange={e=>setFile(e.target.files?.[0]||null)} required/></div><div className="row"><div className="field"><label>Document name</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="Optional"/></div><div className="field"><label>Type</label><select value={type} onChange={e=>setType(e.target.value)}>{TYPES.map(x=><option key={x}>{x}</option>)}</select></div></div><div className="row"><div className="field"><label>Owner</label><input value={owner} onChange={e=>setOwner(e.target.value)}/></div><div className="field"><label>Reference number</label><input value={ref} onChange={e=>setRef(e.target.value)}/></div></div><div className="field"><label>Expiry date</label><input type="date" value={expiry} onChange={e=>setExpiry(e.target.value)}/></div><div className="field"><label>Notes</label><textarea rows={3} value={notes} onChange={e=>setNotes(e.target.value)}/></div><button className="btn" disabled={busy}>{busy?'Uploading...':'Upload securely'}</button></form></div>}

    {showEvent&&<div className="modal" onMouseDown={e=>{if(e.target===e.currentTarget)setShowEvent(false)}}><form className="card" onSubmit={addEvent}><div className="section-title"><h2>Add event</h2><button type="button" className="btn ghost" onClick={()=>setShowEvent(false)}>Close</button></div><div className="field"><label>Title</label><input value={eventTitle} onChange={e=>setEventTitle(e.target.value)} required/></div><div className="field"><label>Date</label><input type="date" value={eventDate} onChange={e=>setEventDate(e.target.value)} required/></div><div className="field"><label>Description</label><textarea rows={3} value={eventDescription} onChange={e=>setEventDescription(e.target.value)}/></div><button className="btn" disabled={busy}>Save event</button></form></div>}
  </main>
}
