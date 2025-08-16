(function(){
	const uniqueEl = document.getElementById('uniqueCount');
	const totalEl = document.getElementById('totalCount');
	const listEl = document.getElementById('uniList');
	const btnSync = document.getElementById('btnSync');
	const syncInfo = document.getElementById('syncInfo');

	async function loadData(){
		try{
			const res = await fetch('universities.json?_=' + Date.now());
			if(!res.ok) throw new Error('HTTP '+res.status);
			return await res.json();
		}catch(e){
			console.error('Failed to load universities.json', e);
			return [];
		}
	}

	function countUnique(unis){
		const names = new Set();
		for(const u of unis){
			if(u && u.name) names.add(u.name.trim());
		}
		return names.size;
	}

	function renderList(unis){
		const seen = new Set();
		const items = [];
		for(const u of unis){
			if(!u || !u.name) continue;
			const key = u.name.trim();
			if(seen.has(key)) continue;
			seen.add(key);
			const city = u.city || u.location || '';
			items.push(`<div class="uni-item"><b>${escapeHtml(key)}</b>${city?` — ${escapeHtml(city)}`:''}</div>`);
		}
		listEl.innerHTML = items.join('');
	}

	function escapeHtml(s){
		return String(s).replace(/[&<>"]+/g, c=>({"&":"&amp;","<":"&lt;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]||c));
	}

	async function refresh(){
		const data = await loadData();
		uniqueEl.textContent = countUnique(data);
		totalEl.textContent = data.length;
		renderList(data);
	}

	async function sync(){
		syncInfo.textContent = 'Синхронизация...';
		try{
			const res = await fetch('http://localhost:8001/sync',{method:'POST'});
			if(!res.ok) throw new Error('HTTP '+res.status);
			syncInfo.textContent = 'Готово';
			await new Promise(r=>setTimeout(r,400));
			await refresh();
		} catch(e){
			syncInfo.textContent = 'Ошибка';
			console.error('Sync error', e);
		}
	}

	btnSync.addEventListener('click', sync);
	refresh();
})(); 