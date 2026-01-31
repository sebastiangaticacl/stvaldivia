document.getElementById("msg").addEventListener("keyup", async (e)=>{
  if(e.key === "Enter"){
    const mensaje = e.target.value;
    const res = await fetch("http://localhost:5001/api/chat",{
      method:"POST",
      headers:{ "Content-Type":"application/json"},
      body:JSON.stringify({mensaje})
    });
    const data = await res.json();
    document.getElementById("chat-box").innerHTML += "<p>"+data.respuesta+"</p>";
  }
});
