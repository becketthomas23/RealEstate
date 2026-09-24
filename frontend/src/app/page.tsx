"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1" ? "" : "http://127.0.0.1:8000");
type Form = { purchase_price:string; closing_cost_rate:string; loan_to_value:string; annual_interest_rate:string; amortization_years:string; exit_cap_rate:string; selling_cost_rate:string; current_potential_gross_income:string; current_operating_expenses:string; vacancy_rate:string; rent_growth_rate:string; expense_growth_rate:string; hold_period_years:string; target_levered_irr:string; minimum_dscr:string; minimum_purchase_price:string; maximum_purchase_price:string };
type OperatingInputs = Pick<Form, "current_potential_gross_income" | "current_operating_expenses" | "vacancy_rate" | "rent_growth_rate" | "expense_growth_rate" | "hold_period_years">;
type Inputs = Pick<Form, "purchase_price" | "closing_cost_rate" | "loan_to_value" | "annual_interest_rate" | "amortization_years" | "exit_cap_rate" | "selling_cost_rate"> & { operating: OperatingInputs };
type Result = { maximum_purchase_price:string; iterations:number; underwriting:{ terminal_noi:string; annual_cash_flows:string[]; operating_projection:{year:number;net_operating_income:string}[]; debt_projection:{year:number;debt_service:string}[]; disposition:{net_sale_proceeds_to_equity:string}; returns:{levered_irr:string;equity_multiple:string;minimum_dscr:string} } };
type SensitivityPoint = { label:string; value:string; maximum_purchase_price:string|null; error:string|null };
type SensitivityDimension = { key:string; label:string; unit:string; points:SensitivityPoint[] };
type SensitivityResult = { dimensions:SensitivityDimension[] };
type Deal = { id:string; name:string; created_at:string; updated_at:string };
type Set = { id:string; deal_id:string; version:number; label:string; source:string|null; effective_date:string; confidence_level:"low"|"medium"|"high"; underwriting:Inputs };
type DealDetail = Deal & { assumption_sets:Set[] };
type Run = { id:string; calculation_type:string; created_at:string; result:Result|SensitivityResult|null; request?:Partial<Pick<Form,"target_levered_irr"|"minimum_dscr"|"minimum_purchase_price"|"maximum_purchase_price">> };
type SavedCalculation = { calculation_run:Run; result:Result };
type SavedSensitivity = { calculation_run:Run; result:SensitivityResult };

const initial:Form = { purchase_price:"1000000", closing_cost_rate:"0.02", loan_to_value:"0.60", annual_interest_rate:"0.05", amortization_years:"30", exit_cap_rate:"0.06", selling_cost_rate:"0.02", current_potential_gross_income:"200000", current_operating_expenses:"50000", vacancy_rate:"0.05", rent_growth_rate:"0.03", expense_growth_rate:"0.02", hold_period_years:"5", target_levered_irr:"0.12", minimum_dscr:"1.20", minimum_purchase_price:"100000", maximum_purchase_price:"3000000" };
const money = new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0});
const percent = new Intl.NumberFormat("en-US",{style:"percent",minimumFractionDigits:1,maximumFractionDigits:1});
const today = () => new Date().toISOString().slice(0,10);
const isSolverResult = (value: Result|SensitivityResult|null): value is Result => value !== null && "maximum_purchase_price" in value;
const isSensitivityResult = (value: Result|SensitivityResult|null): value is SensitivityResult => value !== null && "dimensions" in value;

function toUnderwritingInputs(form: Form): Inputs {
  return {
    purchase_price: form.purchase_price, closing_cost_rate: form.closing_cost_rate, loan_to_value: form.loan_to_value,
    annual_interest_rate: form.annual_interest_rate, amortization_years: form.amortization_years, exit_cap_rate: form.exit_cap_rate,
    selling_cost_rate: form.selling_cost_rate,
    operating: { current_potential_gross_income: form.current_potential_gross_income, current_operating_expenses: form.current_operating_expenses, vacancy_rate: form.vacancy_rate, rent_growth_rate: form.rent_growth_rate, expense_growth_rate: form.expense_growth_rate, hold_period_years: form.hold_period_years },
  };
}

async function api<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(API_URL + path,{...init,headers:{"Content-Type":"application/json",...init?.headers}});
  const data:unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof data === "object" && data !== null && "detail" in data ? (data as {detail:unknown}).detail : null;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => typeof item === "object" && item !== null && "msg" in item ? (item as {msg:unknown}).msg : null)
        .filter((message): message is string => typeof message === "string");
      if (messages.length) throw new Error(messages.join(" "));
    }
    throw new Error(typeof detail === "string" ? detail : "The request could not be completed.");
  }
  return data as T;
}

function Section({title,children}:{title:string;children:ReactNode}) {
  return <section className="border-t border-stone-100 py-6 first:border-t-0 first:pt-0"><h3 className="mb-4 text-sm font-semibold text-stone-900">{title}</h3>{children}</section>;
}
function Field({label,name,form,setForm,suffix,negative}:{label:string;name:keyof Form;form:Form;setForm:(form:Form)=>void;suffix?:string;negative?:boolean}) {
  return <label className="block text-sm font-medium text-stone-700">{label}<span className="relative mt-1.5 block"><input type="number" step="any" min={negative?undefined:"0"} required value={form[name]} onChange={(event)=>setForm({...form,[name]:event.target.value})} className="w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-base outline-none transition focus:border-emerald-700 focus:ring-4 focus:ring-emerald-100"/>{suffix&&<span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-stone-500">{suffix}</span>}</span></label>;
}

export default function Home() {
  const [form,setForm]=useState<Form>(initial);
  const [deals,setDeals]=useState<Deal[]>([]);
  const [deal,setDeal]=useState<DealDetail|null>(null);
  const [activeSet,setActiveSet]=useState<Set|null>(null);
  const [runs,setRuns]=useState<Run[]>([]);
  const [result,setResult]=useState<Result|null>(null);
  const [sensitivity,setSensitivity]=useState<SensitivityResult|null>(null);
  const [dealName,setDealName]=useState("New acquisition");
  const [label,setLabel]=useState("Base case");
  const [source,setSource]=useState("");
  const [effectiveDate,setEffectiveDate]=useState(today);
  const [confidence,setConfidence]=useState<Set["confidence_level"]>("medium");
  const [error,setError]=useState<string|null>(null);
  const [notice,setNotice]=useState<string|null>(null);
  const [loading,setLoading]=useState(false);
  const version=activeSet?"v"+activeSet.version:"Unsaved";
  const fields=(items:Array<[string,keyof Form,string?,boolean?]>)=><div className="grid gap-4 sm:grid-cols-2">{items.map(([labelText,name,suffix,negative])=><Field key={name} label={labelText} name={name} form={form} setForm={setForm} suffix={suffix} negative={negative}/>)}</div>;

  useEffect(()=>{void refreshDeals();},[]);
  async function refreshDeals() {
    try { setDeals(await api<Deal[]>("/v1/deals")); }
    catch { setError("Unable to reach the backend. Start it, then refresh this page."); }
  }
  function applySet(saved:Set) {
    setActiveSet(saved); setLabel(saved.label); setSource(saved.source??""); setEffectiveDate(saved.effective_date); setConfidence(saved.confidence_level);
    const { operating, ...property } = saved.underwriting;
    setForm(current=>({...current,...property,...operating}));
  }
  async function history(id:string,showLatest=false) {
    const found=await api<Run[]>("/v1/assumption-sets/"+id+"/calculation-runs");
    setRuns(found);
    if(showLatest){
      const latestSolver=found.find(run=>isSolverResult(run.result));
      const latestSensitivity=found.find(run=>isSensitivityResult(run.result));
      if(latestSolver&&isSolverResult(latestSolver.result)){
        setResult(latestSolver.result);
        if(latestSolver.request)setForm(current=>({...current,...latestSolver.request}));
      }
      if(latestSensitivity&&isSensitivityResult(latestSensitivity.result))setSensitivity(latestSensitivity.result);
    }
  }
  function newDeal() {
    setDeal(null);setActiveSet(null);setRuns([]);setResult(null);setSensitivity(null);setForm(initial);setDealName("New acquisition");setLabel("Base case");setSource("");setEffectiveDate(today());setConfidence("medium");setError(null);setNotice(null);
  }
  async function openDeal(id:string) {
    if(!id)return newDeal();
    setLoading(true);setError(null);setNotice(null);
    try {
      const opened=await api<DealDetail>("/v1/deals/"+id); setDeal(opened);setDealName(opened.name);
      const newest=opened.assumption_sets[0]??null;setActiveSet(newest);
      if(newest){applySet(newest);await history(newest.id,true);}else{setRuns([]);setResult(null);}
    } catch(caught) { setError(caught instanceof Error?caught.message:"Unable to open the saved deal."); }
    finally {setLoading(false);}
  }
  async function openSet(saved:Set) {
    setLoading(true);setError(null);setNotice(null);
    try {applySet(saved);await history(saved.id,true);}
    catch(caught){setError(caught instanceof Error?caught.message:"Unable to load calculation history.");}
    finally{setLoading(false);}
  }
  async function saveAndSolve(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();setLoading(true);setError(null);setNotice(null);
    try {
      let current=deal;
      if(!current){const created=await api<Deal>("/v1/deals",{method:"POST",body:JSON.stringify({name:dealName})});current={...created,assumption_sets:[]};setDeal(current);}
      const {target_levered_irr,minimum_dscr,minimum_purchase_price,maximum_purchase_price}=form;
      const underwriting=toUnderwritingInputs(form);
      const saved=await api<Set>("/v1/deals/"+current.id+"/assumption-sets",{method:"POST",body:JSON.stringify({label,source:source||null,effective_date:effectiveDate,confidence_level:confidence,underwriting})});
      const calculation=await api<SavedCalculation>("/v1/assumption-sets/"+saved.id+"/maximum-price",{method:"POST",body:JSON.stringify({target_levered_irr,minimum_dscr,minimum_purchase_price,maximum_purchase_price})});
      const updated=await api<DealDetail>("/v1/deals/"+current.id);
      setDeal(updated);applySet(saved);setResult(calculation.result);setSensitivity(null);await history(saved.id);await refreshDeals();
      setNotice("Saved "+current.name+" v"+saved.version+" and recorded the solver run.");
    } catch(caught) {setError(caught instanceof Error?caught.message:"The calculation could not be completed.");}
    finally{setLoading(false);}
  }
  async function calculateSensitivity() {
    if(!activeSet)return;
    setLoading(true);setError(null);setNotice(null);
    try {
      const {target_levered_irr,minimum_dscr,minimum_purchase_price,maximum_purchase_price}=form;
      const calculation=await api<SavedSensitivity>("/v1/assumption-sets/"+activeSet.id+"/sensitivities",{method:"POST",body:JSON.stringify({target_levered_irr,minimum_dscr,minimum_purchase_price,maximum_purchase_price})});
      setSensitivity(calculation.result);await history(activeSet.id);setNotice("Saved the one-way price sensitivity analysis for "+version+".");
    } catch(caught) {setError(caught instanceof Error?caught.message:"The sensitivity analysis could not be completed.");}
    finally{setLoading(false);}
  }

  return <main className="min-h-screen bg-[#f5f6f2] px-4 py-5 text-stone-900 sm:px-7 sm:py-8 lg:px-10"><div className="mx-auto max-w-[1500px]">
    <header className="mb-6 rounded-2xl border border-stone-200 bg-white px-5 py-5 shadow-sm sm:px-7"><div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between"><div><p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-emerald-800">● Underwriting workspace</p><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Price every deal with a clear audit trail.</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">Save an immutable assumption version, solve the maximum supportable price, and return to every calculation later.</p></div><button type="button" onClick={newDeal} className="self-start rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-sm font-semibold text-stone-700 transition hover:border-emerald-700 hover:text-emerald-800">+ New deal</button></div></header>
    <div className="mb-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]"><div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm sm:flex sm:items-center sm:gap-4"><label className="block flex-1 text-xs font-bold uppercase tracking-[0.12em] text-stone-500">Open saved deal<select aria-label="Open saved deal" value={deal?.id??""} onChange={(event)=>void openDeal(event.target.value)} className="mt-2 w-full rounded-xl border border-stone-300 bg-stone-50 px-3 py-2.5 text-sm font-medium text-stone-800 outline-none focus:border-emerald-700"><option value="">Create a new deal</option>{deals.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{deal&&<div className="mt-4 border-t border-stone-100 pt-4 text-xs text-stone-500 sm:mt-0 sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0"><strong className="mr-2 rounded-lg bg-stone-100 px-2 py-1 text-stone-700">{version}</strong>Immutable versions keep every decision traceable.</div>}</div><div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-5 py-4 text-sm text-emerald-950"><p className="font-semibold">{deal?deal.name:"New deal workspace"}</p><p className="mt-1 text-xs text-emerald-800">{deal?deal.assumption_sets.length+" saved versions":"Nothing is saved until you solve."}</p></div></div>
    <div className="grid gap-7 xl:grid-cols-[minmax(0,1fr)_minmax(430px,0.85fr)]"><form onSubmit={saveAndSolve} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7"><div className="mb-6 flex justify-between"><div><h2 className="text-lg font-semibold">Deal assumptions</h2><p className="mt-1 text-sm text-stone-500">Rates use decimal form: 5% = 0.05.</p></div><span className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-stone-600">{version}</span></div>
      <Section title="Version details"><div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm font-medium text-stone-700">Deal name<input value={dealName} onChange={event=>setDealName(event.target.value)} disabled={Boolean(deal)} required className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700 disabled:bg-stone-100"/></label><label className="block text-sm font-medium text-stone-700">Version label<input value={label} onChange={event=>setLabel(event.target.value)} required className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"/></label><label className="block text-sm font-medium text-stone-700">Source<input value={source} onChange={event=>setSource(event.target.value)} placeholder="e.g. Broker OM" className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"/></label><div className="grid grid-cols-2 gap-3"><label className="block text-sm font-medium text-stone-700">Effective date<input type="date" value={effectiveDate} onChange={event=>setEffectiveDate(event.target.value)} required className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"/></label><label className="block text-sm font-medium text-stone-700">Confidence<select value={confidence} onChange={event=>setConfidence(event.target.value as Set["confidence_level"])} className="mt-1.5 w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 outline-none focus:border-emerald-700"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label></div></div></Section>
      <Section title="Acquisition & exit">{fields([["Reference purchase price","purchase_price","USD"],["Closing costs","closing_cost_rate","rate"],["Exit cap rate","exit_cap_rate","rate"],["Selling costs","selling_cost_rate","rate"]])}</Section>
      <Section title="Operations">{fields([["Current potential gross income","current_potential_gross_income","USD / yr"],["Current operating expenses","current_operating_expenses","USD / yr"],["Vacancy","vacancy_rate","rate"],["Rent growth","rent_growth_rate","rate",true],["Expense growth","expense_growth_rate","rate",true],["Hold period","hold_period_years","years"]])}</Section>
      <Section title="Financing">{fields([["Loan-to-value","loan_to_value","rate"],["Interest rate","annual_interest_rate","rate"],["Amortization","amortization_years","years"]])}</Section>
      <Section title="Investment constraints">{fields([["Target levered IRR","target_levered_irr","rate"],["Minimum DSCR","minimum_dscr","x"],["Minimum price bound","minimum_purchase_price","USD"],["Maximum price bound","maximum_purchase_price","USD"]])}</Section>
      {error&&<p role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</p>}{notice&&<p className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{notice}</p>}<button disabled={loading} className="w-full rounded-xl bg-emerald-800 px-4 py-3.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-900 disabled:cursor-wait disabled:opacity-70">{loading?"Saving & solving…":"Save version & solve maximum price"}</button></form>
      <aside className="space-y-5 xl:sticky xl:top-6 xl:self-start"><section className="overflow-hidden rounded-2xl border border-stone-800 bg-[#16201b] p-5 text-stone-100 shadow-sm sm:p-7">{!result?<div className="flex min-h-72 flex-col justify-center"><p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">Results</p><h2 className="mt-3 text-2xl font-semibold">Ready to underwrite.</h2><p className="mt-3 max-w-sm text-sm leading-6 text-stone-300">Your result is saved automatically with the exact assumptions and constraints used to create it.</p></div>:<><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">Maximum supportable price</p><p className="mt-3 text-4xl font-semibold tracking-tight">{money.format(Number(result.maximum_purchase_price))}</p></div><span className="rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-semibold text-stone-200">{result.iterations} iterations</span></div><div className="my-7 grid grid-cols-3 gap-3 border-y border-white/10 py-5 text-center"><div><p className="text-lg font-semibold text-emerald-300">{percent.format(Number(result.underwriting.returns.levered_irr))}</p><p className="mt-1 text-[10px] uppercase tracking-wide text-stone-400">Levered IRR</p></div><div><p className="text-lg font-semibold">{Number(result.underwriting.returns.minimum_dscr).toFixed(2)}x</p><p className="mt-1 text-[10px] uppercase tracking-wide text-stone-400">Min DSCR</p></div><div><p className="text-lg font-semibold">{Number(result.underwriting.returns.equity_multiple).toFixed(2)}x</p><p className="mt-1 text-[10px] uppercase tracking-wide text-stone-400">Equity multiple</p></div></div><div className="grid grid-cols-2 gap-3 rounded-xl bg-white/5 p-3 text-xs"><div><p className="text-stone-400">Terminal NOI</p><p className="mt-1 font-semibold">{money.format(Number(result.underwriting.terminal_noi))}</p></div><div><p className="text-stone-400">Net sale proceeds</p><p className="mt-1 font-semibold">{money.format(Number(result.underwriting.disposition.net_sale_proceeds_to_equity))}</p></div></div><h2 className="mb-3 mt-7 text-base font-semibold">Annual cash flow</h2><div className="overflow-x-auto rounded-xl border border-white/10"><table className="w-full min-w-[420px] text-left text-xs"><thead className="bg-white/5 text-stone-300"><tr><th className="px-3 py-2">Year</th><th className="px-3 py-2 text-right">NOI</th><th className="px-3 py-2 text-right">Debt service</th><th className="px-3 py-2 text-right">Equity cash flow</th></tr></thead><tbody>{result.underwriting.operating_projection.map((year,index)=><tr className="border-t border-white/10" key={year.year}><td className="px-3 py-2.5">{year.year}</td><td className="px-3 py-2.5 text-right">{money.format(Number(year.net_operating_income))}</td><td className="px-3 py-2.5 text-right">{money.format(Number(result.underwriting.debt_projection[index].debt_service))}</td><td className="px-3 py-2.5 text-right font-medium text-emerald-200">{money.format(Number(result.underwriting.annual_cash_flows[index]))}</td></tr>)}</tbody></table></div></>}</section>
      {result&&activeSet&&<section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm"><div className="flex items-start justify-between gap-4"><div><h2 className="text-base font-semibold">One-way price sensitivity</h2><p className="mt-1 text-xs leading-5 text-stone-500">Each case changes one assumption and re-solves the maximum price.</p></div><button type="button" onClick={()=>void calculateSensitivity()} disabled={loading} className="shrink-0 rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-900 disabled:opacity-60">{loading?"Running…":"Run analysis"}</button></div>{sensitivity&&<div className="mt-5 space-y-5">{sensitivity.dimensions.map(dimension=><div key={dimension.key}><div className="mb-2 flex items-center justify-between"><h3 className="text-sm font-semibold text-stone-800">{dimension.label}</h3><span className="text-[10px] uppercase tracking-wide text-stone-500">{dimension.key==="exit_cap_rate"?"±50 bps":"±100 bps"}</span></div><div className="overflow-hidden rounded-xl border border-stone-200"><table className="w-full text-xs"><thead className="bg-stone-50 text-stone-500"><tr><th className="px-3 py-2 text-left font-medium">Case</th><th className="px-3 py-2 text-right font-medium">Input</th><th className="px-3 py-2 text-right font-medium">Max price</th></tr></thead><tbody>{dimension.points.map(point=><tr key={point.label} className="border-t border-stone-100"><td className="px-3 py-2 font-medium text-stone-700">{point.label}</td><td className="px-3 py-2 text-right text-stone-600">{percent.format(Number(point.value))}</td><td className="px-3 py-2 text-right font-semibold text-emerald-800">{point.maximum_purchase_price?money.format(Number(point.maximum_purchase_price)):"Unavailable"}</td></tr>)}</tbody></table></div></div>)}</div>}</section>}
      {deal&&<section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><div><h2 className="text-base font-semibold">Version history</h2><p className="mt-1 text-xs text-stone-500">Inputs remain editable only as a new version.</p></div><span className="text-xs font-semibold text-stone-500">{deal.assumption_sets.length} saved</span></div><div className="mt-4 space-y-2">{deal.assumption_sets.map(saved=><button type="button" key={saved.id} onClick={()=>void openSet(saved)} className={"w-full rounded-xl border p-3 text-left transition "+(activeSet?.id===saved.id?"border-emerald-500 bg-emerald-50":"border-stone-200 hover:bg-stone-50")}><div className="flex items-center justify-between"><span className="text-sm font-semibold">v{saved.version} · {saved.label}</span><span className="text-[10px] font-bold uppercase text-stone-500">{saved.confidence_level}</span></div><p className="mt-1 truncate text-xs text-stone-500">{saved.source||"No source recorded"} · {saved.effective_date}</p></button>)}</div>{runs.length>0&&<div className="mt-5 border-t border-stone-100 pt-4"><p className="mb-2 text-xs font-bold uppercase tracking-wide text-stone-500">Saved runs for {version}</p>{runs.map(run=><button type="button" key={run.id} onClick={()=>{if(isSolverResult(run.result))setResult(run.result);if(isSensitivityResult(run.result))setSensitivity(run.result);}} className="mb-2 flex w-full justify-between rounded-lg bg-stone-50 px-3 py-2 text-left text-xs text-stone-700 hover:bg-emerald-50"><span className="capitalize">{run.calculation_type.replace("_"," ")}</span><span>{new Date(run.created_at).toLocaleDateString()}</span></button>)}</div>}</section>}</aside>
    </div>
  </div></main>;
}
