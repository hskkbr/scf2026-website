"""Browser acceptance checks. Requires Python + playwright and installed Google Chrome.
Run: python -m unittest discover -s tests -v
Optional: SCF_SCREENSHOT_DIR=/tmp/scf-map-screenshots
The server uses a project subpath to exercise GitHub Pages relative URLs.
"""
import functools
import json
import os
import re
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
SPOTS = json.loads((ROOT / 'data/spots.json').read_text())
EVENTS = json.loads((ROOT / 'data/events.json').read_text())


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/scf2026-website/'):
            self.path = self.path.removeprefix('/scf2026-website')
        return super().do_GET()

    def log_message(self, *args):
        pass


class SakyuMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}/scf2026-website/'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='chrome', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':390, 'height':844}, reduced_motion='reduce')
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        # Existing pages have no favicon; exclude only that pre-existing 404.
        self.page.on('console', lambda message: self.errors.append(message.text)
                     if message.type == 'error' and not message.location.get('url', '').endswith('/favicon.ico') else None)
        self.page.goto(self.base + 'sakyu-map.html')
        expect(self.page.locator('#map-controls')).to_be_enabled()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def click_view(self, view):
        self.page.locator(f'[data-view="{view}"]').click()

    def click_filter(self, category):
        self.page.locator(f'[data-filter="{category}"]').click()

    def row(self, item_id):
        return self.page.locator(f'#list-panel > article[data-id="{item_id}"]')

    def screenshot(self, name):
        directory = os.environ.get('SCF_SCREENSHOT_DIR')
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(Path(directory) / name), full_page=True)

    def assert_no_overflow(self):
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))

    def test_01_all_data_details_and_links(self):
        self.assertEqual([s['id'] for s in SPOTS], [f'{i:02}' for i in range(1,17)] + list('ABCDE'))
        self.assertEqual([e['venueRef'] for e in EVENTS], ['B', 'C', 'C'])
        self.click_view('list')
        expect(self.page.locator('#list-panel > article')).to_have_count(24)
        for spot in SPOTS:
            row = self.row(spot['id'])
            expect(row.locator('.spot-id').first).to_have_text(spot['id'])
            row.locator('> .detail-toggle').click()
            details = row.locator('> .accordion-content')
            expect(details.locator('a').filter(has_text='Google Mapsで開く').first).to_have_attribute('href', spot['googleMapsUrl'])
            official = details.get_by_role('link', name='公式サイト（新しいタブで開く）', exact=True)
            expect(official).to_have_count(1 if spot['officialUrl'] else 0)
            if spot['officialUrl']:
                expect(official).to_have_attribute('href', spot['officialUrl'])
            expect(row.locator('> .badges .halloween-badge')).to_have_count(1 if spot['halloween'] else 0)
            expect(details.locator('.detail-description').first).to_have_text(spot['description'])
            row.locator('> .detail-toggle').click()
        self.assertNotIn('recheck', self.page.locator('body').inner_text())
        self.assertNotIn('verified', self.page.locator('body').inner_text())
        expect(self.page.locator('#last-verified')).to_have_text('情報最終確認：2026年10月8日')

    def test_02_filter_state_and_categories(self):
        self.click_filter('food')
        self.click_view('list')
        for category in ['all', '食事', 'カフェ・スイーツ', '軽食・テイクアウト', 'お土産']:
            self.page.locator(f'[data-category="{category}"]').click()
            expected = [s['id'] for s in SPOTS if s['type']=='food' and (category=='all' or category in s['categories'])]
            self.assertEqual(self.page.locator('#list-panel > article').evaluate_all('(rows)=>rows.map(r=>r.dataset.id)'), expected)
            self.click_view('map')
            expect(self.page.locator(f'[data-category="{category}"]')).to_have_attribute('aria-pressed','true')
            self.click_view('list')
            self.assertEqual(self.page.locator('#list-panel > article').evaluate_all('(rows)=>rows.map(r=>r.dataset.id)'), expected)
        self.click_filter('sightseeing')
        expect(self.page.locator('#food-filters')).to_be_hidden()
        expect(self.page.locator('#list-panel > article')).to_have_count(5)
        self.click_filter('event')
        expect(self.page.locator('#list-panel > article')).to_have_count(3)
        self.click_view('map')
        expect(self.page.locator('.spot-marker')).to_have_count(2)
        self.assertEqual(sorted(self.page.locator('.marker-label').evaluate_all('(nodes)=>nodes.map(n=>n.childNodes[0].textContent)')), ['B','C'])
        expect(self.page.locator('.marker-event')).to_have_count(2)

    def test_03_nearby_markers_and_bottom_sheet(self):
        self.click_view('list')
        self.row('09').locator('> .detail-toggle').click()
        self.row('09').get_by_role('button', name='地図で見る', exact=True).click()
        expect(self.page.locator('.leaflet-popup')).to_be_visible()
        expect(self.page.locator('.leaflet-popup')).to_contain_text('09 Totto PURIN')
        expect(self.page.locator('.spot-marker.is-selected')).to_have_count(1)
        # 09/10 have identical coordinates; they must both be selectable after spiderfy.
        for item_id in ['09','10','14','16']:
            marker = self.page.locator(f'.spot-marker[title^="{item_id} "]')
            expect(marker).to_be_visible()
        self.assertGreaterEqual(self.page.locator('.leaflet-marker-pane .spot-marker').count(), 4)
        self.page.locator('.leaflet-popup button').click()
        expect(self.page.locator('#detail-sheet')).to_be_visible()
        expect(self.page.locator('#sheet-title')).to_contain_text('09 Totto PURIN')
        rect = self.page.locator('#detail-sheet').bounding_box()
        self.assertAlmostEqual(rect['y'] + rect['height'], 844, delta=2)
        for _ in range(10):
            self.page.keyboard.press('Tab')
            self.assertTrue(self.page.evaluate("document.getElementById('detail-sheet').contains(document.activeElement)"))
        self.screenshot('mobile-detail.png')
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#detail-sheet')).not_to_be_visible()
        expect(self.page.locator('.leaflet-popup button')).to_be_focused()
        self.page.locator('.leaflet-popup-close-button').click()
        marker = self.page.locator('.spot-marker[title^="10 "]')
        marker.focus()
        self.page.keyboard.press('Enter')
        expect(self.page.locator('.leaflet-popup')).to_contain_text('10 さんかく氷')

    def test_04_events_and_venue_navigation(self):
        self.click_view('list')
        for venue, event_ids in [('B',['EV01']), ('C',['EV02','EV03'])]:
            row = self.row(venue)
            row.locator('> .detail-toggle').click()
            expect(row.locator('.related-events')).to_contain_text('10/24 開催イベント')
            for event_id in event_ids:
                expect(row.locator(f'article[data-id="{event_id}"]')).to_be_visible()
            row.locator('> .detail-toggle').click()
        self.click_filter('event')
        row = self.row('EV03')
        row.locator('> .detail-toggle').click()
        for notice in EVENTS[2]['notices']:
            expect(row.locator('.detail-notices')).to_contain_text(notice)
        expect(row.get_by_role('link', name='イベント詳細を見る（新しいタブで開く）')).to_have_attribute('href', EVENTS[2]['eventUrl'])
        expect(row.get_by_role('link', name='イベント詳細を見る（新しいタブで開く）')).to_have_attribute('target','_blank')
        self.screenshot('mobile-event.png')
        row.get_by_role('button', name='会場を地図で見る').click()
        expect(self.page.locator('[data-filter="event"]')).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('.leaflet-popup')).to_contain_text('C 鳥取砂丘 砂の美術館')
        self.page.locator('.leaflet-popup button').click()
        expect(self.page.locator('#detail-sheet .halloween-badge')).to_have_count(0)
        expect(self.page.locator('#detail-sheet .related-events > article')).to_have_count(2)

    def test_05_viewports_and_existing_pages(self):
        self.page.wait_for_function("document.querySelectorAll('.leaflet-tile-loaded').length > 0")
        for width in [360,390,430,768,1024,1440]:
            self.page.set_viewport_size({'width':width, 'height':900})
            self.click_view('map')
            self.page.locator('#fit-map').click()
            self.assert_no_overflow()
            self.click_filter('food')
            self.page.locator('[data-category="軽食・テイクアウト"]').click()
            self.assert_no_overflow()
            self.click_view('list')
            self.row('15').locator('> .detail-toggle').click()
            self.assert_no_overflow()
            self.click_filter('all')
        self.page.set_viewport_size({'width':1440,'height':1000})
        self.click_view('map')
        self.page.locator('#fit-map').click()
        self.page.wait_for_timeout(600)
        self.screenshot('desktop-map.png')
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.locator('#fit-map').click()
        self.page.wait_for_timeout(600)
        self.screenshot('mobile-map.png')
        self.click_view('list')
        self.click_filter('food')
        self.page.locator('[data-category="お土産"]').click()
        self.screenshot('mobile-list.png')
        for name in ['index.html','access.html','poster.html']:
            self.page.goto(self.base + name)
            self.assertEqual(self.page.locator('link[href="sakyu-map.css"]').count(), 0)
            self.page.locator('.nav-toggle').click()
            expect(self.page.locator('#nav-links')).to_be_visible()
            self.page.keyboard.press('Escape')
            expect(self.page.locator('#nav-links')).not_to_be_visible()
        self.page.goto(self.base + 'index.html')
        expect(self.page.locator('a[href="sakyu-map.html"]')).to_have_count(2)

    def test_06_cluster_keyboard_and_spiderfy(self):
        cluster = self.page.locator('.cluster-marker').first
        expect(cluster).to_have_attribute('aria-label', re.compile('地点を展開'))
        cluster.focus()
        self.page.keyboard.press('Enter')
        self.assertGreater(self.page.locator('.spot-marker').count(), 1)
        for marker in self.page.locator('.spot-marker').all():
            expect(marker).to_have_attribute('aria-label', re.compile('飲食店|観光'))


if __name__ == '__main__':
    unittest.main()
