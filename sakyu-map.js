(() => {
    'use strict';

    const $ = (id) => document.getElementById(id);
    const state = { view: 'map', filter: 'all', category: 'all', selectedId: null };
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let spots = [], events = [], map, clusters;
    let detailSequence = 0;
    let mapNeedsFit = false;
    let sheetOpener = null;
    const markers = new Map();

    // All visitor-facing content comes from the JSON, never from management status.
    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }
    function button(text, action, className = 'btn') {
        const node = el('button', className, text);
        node.type = 'button';
        node.addEventListener('click', action);
        return node;
    }
    function externalLink(text, url, secondary = false) {
        const link = el('a', `btn${secondary ? ' btn-secondary' : ''}`, text);
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.setAttribute('aria-label', `${text}（新しいタブで開く）`);
        return link;
    }
    const venueFor = (event) => spots.find((spot) => spot.id === event.venueRef);
    const eventsFor = (spot) => events.filter((event) => event.venueRef === spot.id);
    const sessionTime = (session) => `${session.start}〜${session.end || ''}`;
    const sessionsText = (event, availableOnly = false) => event.sessions
        .filter((session) => !availableOnly || session.scfAvailable).map(sessionTime).join('／');

    function heading(item, tag = 'h3') {
        const node = el(tag, 'row-heading');
        node.append(el('span', `spot-id ${item.type === 'event' ? 'event-id' : item.type}`, item.id), ' ', el('span', '', item.name));
        return node;
    }
    function badges(spot) {
        const node = el('div', 'badges');
        spot.categories.forEach((category) => node.append(el('span', 'category-badge', category)));
        if (spot.halloween) node.append(el('span', 'halloween-badge', '🎃 ハロウィン仕様'));
        if (eventsFor(spot).length) node.append(el('span', 'event-badge', 'EVENT'));
        return node;
    }
    function facts(entries) {
        const dl = el('dl', 'detail-facts');
        entries.filter(([, value]) => value !== undefined && value !== null).forEach(([label, value]) => {
            const row = el('div');
            row.append(el('dt', '', label), el('dd', '', value));
            dl.append(row);
        });
        return dl;
    }
    function notices(item) {
        const box = el('div', 'detail-notices');
        box.append(el('p', '', 'ご利用・参加にあたって'));
        const list = el('ul');
        item.notices.forEach((notice) => list.append(el('li', '', notice)));
        box.append(list);
        return box;
    }
    function detail(item, inSheet = false) {
        const content = el('div');
        const isEvent = item.type === 'event';
        const venue = isEvent ? venueFor(item) : item;
        if (inSheet) {
            const title = heading(item, 'h2');
            title.id = 'sheet-title';
            content.append(title);
            if (!isEvent) content.append(badges(item));
        }
        content.append(el('p', 'detail-description', item.description));
        content.append(facts(isEvent ? [
            ['開催日', item.date.replace(/-/g, '/')],
            ['会場', `${venue.id} ${venue.name}`],
            ['開催時間', sessionsText(item)],
            ['SCF時間内', item.scfEventHours],
            ['料金', item.price],
            ['最終受付', item.lastEntry],
            ['受付・予約', item.reservation],
            ['天候', item.weatherPolicy],
            ['定員', item.capacity],
            ['制作時間', item.duration],
            ['持ち帰り', item.takeHomeAllowed === false ? 'できません' : null]
        ] : [
            ['通常営業時間', item.hours], ['SCF時間内', item.eventHours], ['価格帯', item.price]
        ]));
        if (item.notices.length) content.append(notices(item));
        const actions = el('div', 'detail-actions');
        actions.append(externalLink('Google Mapsで開く', venue.googleMapsUrl));
        if (isEvent) actions.append(externalLink('イベント詳細を見る', item.eventUrl, true));
        else if (item.officialUrl) actions.append(externalLink('公式サイト', item.officialUrl, true));
        if (!inSheet || isEvent) {
            actions.append(button(isEvent ? '会場を地図で見る' : '地図で見る', () => {
                closeSheet();
                showOnMap(venue.id);
            }, 'btn btn-secondary'));
        }
        content.append(actions);
        if (!isEvent && eventsFor(item).length) {
            const related = el('div', 'related-events');
            related.append(el('h3', '', '10/24 開催イベント'));
            eventsFor(item).forEach((event) => related.append(compactRow(event, 'h4')));
            content.append(related);
        }
        return content;
    }
    function compactRow(item, headingTag = 'h3') {
        const row = el('article', 'compact-row');
        row.dataset.id = item.id;
        row.append(heading(item, headingTag));
        if (item.type === 'event') {
            const venue = venueFor(item);
            row.append(el('p', 'row-meta', `${venue.id} ${venue.name}`));
            row.append(el('p', 'row-meta', `開催時間 ${sessionsText(item, true)}`));
            row.append(el('p', 'row-meta', `SCF時間内 ${item.scfEventHours}`));
        } else {
            row.append(badges(item));
            row.append(el('p', 'row-meta', `SCF時間内 ${item.eventHours}`));
        }
        row.append(el('p', 'row-meta', item.price));
        row.append(el('p', 'row-summary', item.description));
        const content = el('div', 'accordion-content');
        content.id = `detail-${++detailSequence}`;
        content.hidden = true;
        const toggle = button('詳細を見る', () => {
            const open = content.hidden;
            if (open && !content.childElementCount) content.append(detail(item));
            content.hidden = !open;
            toggle.textContent = open ? '詳細を閉じる' : '詳細を見る';
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', `${item.id} ${item.name}の${open ? '詳細を閉じる' : '詳細を見る'}`);
        }, 'detail-toggle');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-controls', content.id);
        toggle.setAttribute('aria-label', `${item.id} ${item.name}の詳細を見る`);
        row.append(toggle, content);
        return row;
    }
    function openSheet(spot, opener) {
        sheetOpener = opener;
        $('sheet-content').replaceChildren(detail(spot, true));
        $('detail-sheet').showModal();
        $('detail-sheet').scrollTop = 0;
        $('close-sheet').focus({ preventScroll: true });
    }
    function closeSheet() {
        if ($('detail-sheet').open) $('detail-sheet').close();
    }
    $('close-sheet').addEventListener('click', closeSheet);
    $('detail-sheet').addEventListener('keydown', (event) => {
        if (event.key !== 'Tab') return;
        const focusable = [...$('detail-sheet').querySelectorAll('button, a[href], [tabindex="0"]')]
            .filter((node) => !node.disabled && node.getClientRects().length);
        const first = focusable[0], last = focusable.at(-1);
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });
    $('detail-sheet').addEventListener('click', (event) => {
        if (event.target !== $('detail-sheet')) return;
        const rect = $('detail-sheet').getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeSheet();
    });
    $('detail-sheet').addEventListener('close', () => {
        if (sheetOpener?.isConnected) sheetOpener.focus({ preventScroll: true });
    });

    function visibleSpots() {
        if (state.filter === 'event') return spots.filter((spot) => eventsFor(spot).length);
        return spots.filter((spot) => (state.filter === 'all' || spot.type === state.filter) &&
            (state.filter !== 'food' || state.category === 'all' || spot.categories.includes(state.category)));
    }
    function renderList() {
        const list = $('list-panel');
        list.replaceChildren();
        if (state.filter !== 'event') {
            list.append(el('h2', 'list-heading', 'スポット一覧'));
            visibleSpots().forEach((spot) => list.append(compactRow(spot)));
        }
        if (state.filter === 'all' || state.filter === 'event') {
            list.append(el('h2', 'list-heading', '10/24 開催イベント'));
            events.forEach((event) => list.append(compactRow(event)));
        }
    }
    function updateControls() {
        document.querySelectorAll('[data-view]').forEach((node) => node.setAttribute('aria-pressed', String(node.dataset.view === state.view)));
        document.querySelectorAll('[data-filter]').forEach((node) => node.setAttribute('aria-pressed', String(node.dataset.filter === state.filter)));
        document.querySelectorAll('[data-category]').forEach((node) => node.setAttribute('aria-pressed', String(node.dataset.category === state.category)));
        $('food-filters').hidden = state.filter !== 'food';
        const labels = { all: 'すべて', food: '飲食店', sightseeing: '観光', event: 'イベント' };
        const label = labels[state.filter] + (state.filter === 'food' && state.category !== 'all' ? `・${state.category}` : '');
        $('results-count').textContent = state.filter === 'event'
            ? `${label}：${events.length}件／会場${visibleSpots().length}地点`
            : `${label}：${visibleSpots().length}地点${state.filter === 'all' ? `／イベント${events.length}件` : ''}`;
    }
    function switchView(view) {
        state.view = view;
        $('map-panel').hidden = view !== 'map';
        $('list-panel').hidden = view !== 'list';
        updateControls();
        if (view === 'map' && map) {
            map.invalidateSize({ pan: false });
            if (mapNeedsFit) fitVisible();
        }
    }
    function setSelected(id) {
        state.selectedId = id;
        markers.forEach((marker, markerId) => {
            marker.getElement()?.classList.toggle('is-selected', markerId === id);
        });
    }
    function fitVisible() {
        if (!map) return;
        const bounds = visibleSpots().map((spot) => [spot.location.latitude, spot.location.longitude]);
        if (bounds.length) map.fitBounds(bounds, { padding: [45, 55], maxZoom: 17, animate: false });
        mapNeedsFit = false;
    }
    function showOnMap(id) {
        switchView('map');
        const marker = markers.get(id);
        if (!map || !marker) return;
        // Keep the active filter. Event cards only navigate to their visible B/C venues.
        $('sakyu-map').scrollIntoView({ behavior: 'instant', block: 'center' });
        map.setView(marker.getLatLng(), map.getMaxZoom(), { animate: false });
        clusters.zoomToShowLayer(marker, () => {
            setSelected(id);
            marker.openPopup();
            marker.getPopup().getElement()?.querySelector('button')?.focus({ preventScroll: true });
        });
    }
    function popup(spot) {
        const content = el('div');
        content.append(el('strong', 'popup-title', `${spot.id} ${spot.name}`));
        content.append(el('p', '', spot.categories.join('・')));
        content.append(el('p', '', spot.eventHours));
        const more = button('詳細を見る', () => openSheet(spot, more));
        more.setAttribute('aria-label', `${spot.id} ${spot.name}の詳細を見る`);
        content.append(more);
        return content;
    }
    function decorateMarker(marker, spot) {
        const node = marker.getElement();
        if (!node) return;
        node.setAttribute('aria-label', `${spot.id} ${spot.name}、${spot.type === 'food' ? '飲食店' : '観光'}${eventsFor(spot).length ? '、イベント開催会場' : ''}`);
        node.classList.toggle('is-selected', state.selectedId === spot.id);
        node.onkeydown = (event) => {
            if (event.key === ' ') {
                event.preventDefault();
                marker.openPopup();
            }
        };
    }
    function initMap() {
        if (!window.L?.markerClusterGroup) {
            $('map-error').textContent = '地図を読み込めませんでした。リスト表示から各地点の詳細とGoogle Mapsをご利用ください。';
            $('map-error').hidden = false;
            switchView('list');
            return;
        }
        map = L.map('sakyu-map', { maxZoom: 19, minZoom: 12, zoomControl: false,
            zoomAnimation: !reducedMotion.matches, fadeAnimation: !reducedMotion.matches, markerZoomAnimation: !reducedMotion.matches });
        L.control.zoom({ zoomInTitle: '地図を拡大', zoomOutTitle: '地図を縮小' }).addTo(map);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).on('tileerror', () => {
            $('map-error').textContent = '地図画像を読み込めない部分があります。リスト表示やGoogle Mapsもご利用いただけます。';
            $('map-error').hidden = false;
        }).addTo(map);
        clusters = L.markerClusterGroup({
            maxClusterRadius: 48, spiderfyOnMaxZoom: true, zoomToBoundsOnClick: false,
            showCoverageOnHover: false, spiderfyDistanceMultiplier: 1.8, animate: !reducedMotion.matches,
            iconCreateFunction(cluster) {
                const label = el('span', '', String(cluster.getChildCount()));
                label.append(el('small', '', '地点'));
                // The icon DOM is attached just after this callback returns.
                queueMicrotask(() => labelClusters());
                return L.divIcon({ html: label, className: 'cluster-marker', iconSize: [48, 48] });
            }
        });
        const expandCluster = (cluster) => {
            map.panTo(cluster.getLatLng(), { animate: false });
            cluster.spiderfy();
        };
        clusters.on('clusterclick', (event) => expandCluster(event.layer));
        clusters.on('spiderfied', (event) => {
            event.markers.forEach((marker) => decorateMarker(marker, spots.find((spot) => spot.id === marker.options.spotId)));
        });
        spots.forEach((spot) => {
            const label = el('span', `marker-label ${spot.type}`, spot.id);
            if (eventsFor(spot).length) label.append(el('span', 'marker-event', 'EVENT'));
            const marker = L.marker([spot.location.latitude, spot.location.longitude], {
                icon: L.divIcon({ html: label, className: 'spot-marker', iconSize: [44, 44], iconAnchor: [22, 22], popupAnchor: [0, -24] }),
                title: `${spot.id} ${spot.name}`, keyboard: true, spotId: spot.id
            });
            marker.bindPopup(() => popup(spot), { maxWidth: 260, minWidth: 185, autoPanPadding: [20, 50] });
            marker.on('add', () => decorateMarker(marker, spot));
            marker.on('popupopen', () => setSelected(spot.id));
            markers.set(spot.id, marker);
        });
        map.addLayer(clusters);
        // Give clusters descriptive keyboard labels, including their constituent IDs.
        const labelClusters = () => {
            const seen = new Set();
            markers.forEach((marker) => {
                const parent = clusters.getVisibleParent(marker);
                if (!parent?.getAllChildMarkers || seen.has(parent)) return;
                seen.add(parent);
                const node = parent.getElement();
                if (!node) return;
                const names = parent.getAllChildMarkers().map((child) => child.options.title).join('、');
                node.setAttribute('aria-label', `${parent.getChildCount()}地点を展開：${names}`);
                node.setAttribute('role', 'button');
                node.onkeydown = (event) => {
                    if (event.key === ' ' || event.key === 'Enter') {
                        event.preventDefault();
                        expandCluster(parent);
                    }
                };
            });
        };
        map.on('moveend zoomend', labelClusters);
        clusters.on('animationend unspiderfied', labelClusters);
    }
    function applyFilter() {
        closeSheet();
        setSelected(null);
        map?.closePopup();
        if (clusters) {
            clusters.clearLayers();
            clusters.addLayers(visibleSpots().map((spot) => markers.get(spot.id)));
            mapNeedsFit = true;
            if (state.view === 'map') fitVisible();
        }
        renderList();
        updateControls();
    }
    document.querySelectorAll('[data-view]').forEach((node) => node.addEventListener('click', () => switchView(node.dataset.view)));
    document.querySelectorAll('[data-filter]').forEach((node) => node.addEventListener('click', () => {
        state.filter = node.dataset.filter;
        applyFilter();
    }));
    document.querySelectorAll('[data-category]').forEach((node) => node.addEventListener('click', () => {
        state.category = node.dataset.category;
        applyFilter();
    }));
    $('fit-map').addEventListener('click', fitVisible);
    $('reload-data').addEventListener('click', () => window.location.reload());

    async function loadData() {
        try {
            [spots, events] = await Promise.all(['data/spots.json', 'data/events.json'].map(async (url) => {
                const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
                if (!response.ok) throw new Error(`Failed to load ${url}`);
                return response.json();
            }));
            const latest = [...spots, ...events].map((item) => item.lastVerified).sort().at(-1);
            const [year, month, day] = latest.split('-').map(Number);
            $('last-verified').textContent = `情報最終確認：${year}年${month}月${day}日`;
            // Render a usable list even when the map library cannot be loaded.
            renderList();
            initMap();
            applyFilter();
            $('map-controls').disabled = false;
        } catch (error) {
            $('results-count').textContent = 'データの読み込みに失敗しました。';
            $('load-error').hidden = false;
            $('map-panel').hidden = true;
        }
    }
    loadData();
})();
