(function(){
	console.log('🚀 Universities.js загружен');
	
	const grid = document.getElementById('uniGrid');
	const searchInput = document.getElementById('searchInput');
	const specFilter = document.getElementById('specFilter');

	console.log('🔍 Найденные элементы:', { grid, searchInput, specFilter });

	let universities = [];
	let specializations = [];

	function render(list){
		console.log('🎨 Рендеринг списка:', list?.length || 0);
		
		// Группируем вузы по названию и городу
		const groupedUnis = {};
		list.forEach(u => {
			const key = `${u.name}|${u.city}`;
			if (!groupedUnis[key]) {
				groupedUnis[key] = {
					name: u.name,
					city: u.city,
					url: '',
					specializations: []
				};
			}
			// Добавляем специальность только если её ещё нет
			const specExists = groupedUnis[key].specializations.some(s => s.name === u.specialization);
			if (!specExists && u.specialization) {
				groupedUnis[key].specializations.push({
					name: u.specialization,
					score_min: u.score_min,
					score_max: u.score_max
				});
			}
			// Сохраняем URL от первой специальности, которая его имеет
			if (u.url && !groupedUnis[key].url) {
				groupedUnis[key].url = u.url;
			}
		});
		
		// Обновляем статистику
		const uniqueUnis = Object.keys(groupedUnis).length;
		const uniqueSpecs = new Set();
		list.forEach(u => { if(u.specialization) uniqueSpecs.add(u.specialization); });
		
		const uniqueCount = document.getElementById('uniqueUniCount');
		const totalCount = document.getElementById('totalSpecsCount');
		
		if (uniqueCount) {
			const uniText = getRussianPlural(uniqueUnis, 'вуз', 'вуза', 'вузов');
			uniqueCount.textContent = `${uniqueUnis} ${uniText}`;
		}
		if (totalCount) {
			const specCount = uniqueSpecs.size;
			const specText = getRussianPlural(specCount, 'специальность', 'специальности', 'специальностей');
			totalCount.textContent = `${specCount} ${specText}`;
		}
		
		if(!grid) {
			console.error('❌ Grid элемент не найден!');
			return;
		}
		if(!list || list.length === 0){
			grid.innerHTML = '<div class="uni-empty">Ничего не найдено</div>';
			return;
		}
		
		grid.innerHTML = Object.values(groupedUnis).map(uni => {
			// Сортируем специальности по названию
			const sortedSpecs = [...uni.specializations].sort((a, b) => a.name.localeCompare(b.name));
			
			const specializationsHtml = sortedSpecs.map(spec => {
				const score = (spec.score_min != null && spec.score_max != null)
					? `${spec.score_min}-${spec.score_max}`
					: '—';
				return `
					<div class="spec-item">
						<span class="spec-name">${escapeHtml(spec.name)}</span>
						<span class="spec-score">${score}</span>
					</div>
				`;
			}).join('');
			
			const link = uni.url ? `<a class="btn btn-primary" href="${uni.url}" target="_blank" rel="noopener">Перейти на сайт</a>` : '';
			
			return `
				<div class="uni-card">
					<div class="uni-card-head">
						<h3 class="uni-title">${escapeHtml(uni.name)}</h3>
					</div>
					<div class="uni-location">
						<i class="fas fa-location-dot"></i>
						<span>${escapeHtml(uni.city || '—')}</span>
					</div>
					<div class="uni-specializations">
						<h4>Специальности (${sortedSpecs.length}):</h4>
						<div class="spec-list">
							${specializationsHtml}
						</div>
					</div>
					<div class="uni-actions">
						${link}
					</div>
				</div>
			`;
		}).join('');
		console.log('✅ Рендеринг завершен');
	}

	function escapeHtml(str){
		return String(str)
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#039;');
	}
	
	// Функция для правильных окончаний в русском языке
	function getRussianPlural(count, one, two, five) {
		const mod10 = count % 10;
		const mod100 = count % 100;
		
		if (mod100 >= 11 && mod100 <= 19) return five;
		if (mod10 === 1) return one;
		if (mod10 >= 2 && mod10 <= 4) return two;
		return five;
	}

	function applyFilters(){
		const q = (searchInput.value || '').toLowerCase().trim();
		const spec = specFilter.value;
		
		let filtered = universities;
		
		// Фильтруем по поисковому запросу
		if (q) {
			filtered = filtered.filter(u => 
				(u.name && u.name.toLowerCase().includes(q)) || 
				(u.city && u.city.toLowerCase().includes(q))
			);
		}
		
		// Фильтруем по специализации
		if (spec) {
			filtered = filtered.filter(u => u.specialization === spec);
		}
		
		render(filtered);
	}

	function populateSpecs(){
		// Очищаем существующие опции, кроме первой
		while (specFilter.children.length > 1) {
			specFilter.removeChild(specFilter.lastChild);
		}
		
		const set = new Set();
		universities.forEach(u => { if(u.specialization){ set.add(u.specialization); } });
		specializations = Array.from(set).sort();
		specializations.forEach(s => {
			const opt = document.createElement('option');
			opt.value = s;
			opt.textContent = s;
			specFilter.appendChild(opt);
		});
	}

	function initEvents(){
		searchInput.addEventListener('input', applyFilters);
		specFilter.addEventListener('change', applyFilters);
		
		// Добавляем обработчик для кнопки обновления
		const refreshBtn = document.getElementById('refreshBtn');
		if (refreshBtn) {
			refreshBtn.addEventListener('click', () => {
				console.log('🔄 Ручное обновление данных...');
				refreshBtn.classList.add('loading');
				loadData().finally(() => {
					refreshBtn.classList.remove('loading');
				});
			});
		}
	}

	// Попытка загрузить данные
	function loadData() {
		console.log('🔄 Начинаю загрузку данных...');
		console.log('🔍 Проверяю встроенные данные:', window.EMBEDDED_UNIVERSITIES);
		
		return new Promise((resolve, reject) => {
			// Сначала проверяем встроенные данные
			if (window.EMBEDDED_UNIVERSITIES && window.EMBEDDED_UNIVERSITIES.length > 0) {
				console.log('✅ Использую встроенные данные, вузов:', window.EMBEDDED_UNIVERSITIES.length);
				universities = window.EMBEDDED_UNIVERSITIES;
				populateSpecs();
				initEvents();
				render(universities);
				resolve();
				return;
			}
			
			console.log('📡 Встроенных данных нет, загружаю universities.json...');
			
			// Если встроенных данных нет, пробуем загрузить через fetch
			fetch('universities.json', { 
				cache: 'no-store',
				method: 'GET',
				headers: {
					'Cache-Control': 'no-cache',
					'Pragma': 'no-cache'
				}
			})
			.then(r => {
				console.log('📡 Ответ сервера:', r.status, r.statusText);
				if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
				return r.text();
			})
			.then(text => {
				console.log('📄 Получен текст длиной:', text.length);
				try {
					const data = JSON.parse(text);
					console.log('✅ JSON успешно распарсен, вузов:', data.length);
					universities = Array.isArray(data) ? data : [];
					populateSpecs();
					initEvents();
					render(universities);
					resolve();
				} catch (parseError) {
					console.error('❌ Ошибка парсинга JSON:', parseError);
					reject(parseError);
				}
			})
			.catch(err => {
				console.error('❌ Ошибка загрузки universities.json:', err);
				console.error('❌ Детали ошибки:', err.message);
				console.log('🔄 Переключаюсь на демо-данные...');
				// Показываем демо-данные если не удалось загрузить
				universities = getDemoData();
				populateSpecs();
				initEvents();
				render(universities);
				resolve(); // Разрешаем промис даже с демо-данными
			});
		});
	}

	// Демо-данные на случай если JSON не загружается
	function getDemoData() {
		return [
			{
				"name": "БелГУ",
				"location": "Белгород",
				"score_min": 220,
				"score_max": 250,
				"url": "https://bsu.edu.ru",
				"specialization": "Программная инженерия"
			},
			{
				"name": "ВГУ",
				"location": "Воронеж",
				"score_min": 225,
				"score_max": 255,
				"url": "https://www.vsu.ru",
				"specialization": "Data Science"
			},
			{
				"name": "МГУ",
				"location": "Москва",
				"score_min": 280,
				"score_max": 300,
				"url": "https://www.msu.ru",
				"specialization": "AI/ML инженерия"
			}
		];
	}

	// Ждем загрузки DOM
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', loadData);
	} else {
		loadData();
	}
	
	// Автоматическое обновление данных каждые 30 секунд
	setInterval(() => {
		console.log('🔄 Проверка обновлений...');
		loadData();
	}, 30000);
})(); 