async function loadStatus(){
  const res = await fetch("http://localhost:5002/api/panel/status");
  const data = await res.json();
  document.getElementById("status").innerHTML =
    "<pre>"+JSON.stringify(data,null,2)+"</pre>";
}
