import { expect, test, type ConsoleMessage, type Page, type Response } from '@playwright/test';

type DiscoveredIds = {
  entryId?: string;
  categorySlug?: string;
  clusterId?: string;
  entityName?: string;
  arcId?: string;
  storyId?: string;
  topic?: string;
};

const FRONTEND_BASE_URL = (process.env.FRONTEND_BASE_URL || 'https://frontend-chi-brown-98.vercel.app').replace(/\/$/, '');
const API_BASE_URL = (process.env.API_BASE_URL || 'https://smartnews-api.onrender.com').replace(/\/$/, '');

async function discoverIds(): Promise<DiscoveredIds> {
  const ids: DiscoveredIds = {};

  const homeRes = await fetch(`${API_BASE_URL}/api/home`);
  if (homeRes.ok) {
    const home = await homeRes.json();
    ids.entryId = home?.top_stories?.[0]?.entry_id;
    ids.topic = home?.trending_topics?.[0]?.topic;
  }

  const categoriesRes = await fetch(`${API_BASE_URL}/api/categories`);
  if (categoriesRes.ok) {
    const categories = await categoriesRes.json();
    ids.categorySlug = categories?.categories?.[0]?.slug;
  }

  const clustersRes = await fetch(`${API_BASE_URL}/api/clusters`);
  if (clustersRes.ok) {
    const clusters = await clustersRes.json();
    ids.clusterId = String(clusters?.[0]?.cluster_id || '');
  }

  const entitiesRes = await fetch(`${API_BASE_URL}/api/entities?limit=1`);
  if (entitiesRes.ok) {
    const entities = await entitiesRes.json();
    ids.entityName = entities?.entities?.[0]?.entity_name;
  }

  const narrativesRes = await fetch(`${API_BASE_URL}/api/narratives?limit=1`);
  if (narrativesRes.ok) {
    const narratives = await narrativesRes.json();
    ids.arcId = narratives?.items?.[0]?.arc_id;
  }

  const storiesRes = await fetch(`${API_BASE_URL}/api/stories?limit=1`);
  if (storiesRes.ok) {
    const stories = await storiesRes.json();
    ids.storyId = stories?.items?.[0]?.story_id;
  }

  return ids;
}

async function assertRouteHealthy(page: Page, path: string) {
  const routeErrors: string[] = [];

  const onPageError = (error: Error) => {
    routeErrors.push(`pageerror: ${error.message}`);
  };

  const onConsole = (msg: ConsoleMessage) => {
    if (msg.type() === 'error') {
      routeErrors.push(`console.error: ${msg.text()}`);
    }
  };

  const onResponse = (response: Response) => {
    const url = response.url();
    const status = response.status();
    if (url.startsWith(FRONTEND_BASE_URL) && status >= 500) {
      routeErrors.push(`http ${status}: ${url}`);
    }
  };

  const onRequestFailed = (request: { url: () => string; failure: () => { errorText?: string } | null }) => {
    const url = request.url();
    const failure = request.failure();
    const errorText = failure?.errorText || 'unknown';
    const isAbortedRscPrefetch = errorText.includes('ERR_ABORTED') && url.includes('_rsc=');
    if (isAbortedRscPrefetch) {
      return;
    }
    if (url.startsWith(FRONTEND_BASE_URL)) {
      routeErrors.push(`requestfailed: ${url} (${errorText})`);
    }
  };

  page.on('pageerror', onPageError);
  page.on('console', onConsole);
  page.on('response', onResponse);
  page.on('requestfailed', onRequestFailed);

  let response = null;
  let navError: unknown = null;
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      response = await page.goto(`${FRONTEND_BASE_URL}${path}`, {
        waitUntil: 'domcontentloaded',
        timeout: 45000,
      });
      navError = null;
      break;
    } catch (err) {
      navError = err;
      if (attempt < 2) {
        await page.waitForTimeout(1500);
        continue;
      }
    }
  }

  expect(navError, `Navigation failed for ${path}: ${String(navError)}`).toBeNull();

  expect(response, `No response for ${path}`).not.toBeNull();
  expect(response?.status(), `Unexpected status for ${path}`).toBeLessThan(400);

  const body = page.locator('body');
  await expect(body).toBeVisible();
  await expect(body).not.toContainText(/Application error|Internal Server Error|Unhandled Runtime Error/i);
  await expect(page.locator('a[href]').first()).toBeVisible();

  await page.waitForTimeout(500);
  expect(routeErrors, `Runtime errors detected on ${path}:\n${routeErrors.join('\n')}`).toEqual([]);

  page.off('pageerror', onPageError);
  page.off('console', onConsole);
  page.off('response', onResponse);
  page.off('requestfailed', onRequestFailed);
}

test('live user journey across critical routes', async ({ page }) => {
  const ids = await discoverIds();

  const routes = [
    '/',
    '/briefing',
    '/sources',
    '/stories',
    '/narratives',
    '/search?q=ai',
  ];

  if (ids.entryId) routes.push(`/article/${encodeURIComponent(ids.entryId)}`);
  if (ids.categorySlug) routes.push(`/category/${encodeURIComponent(ids.categorySlug)}`);
  if (ids.clusterId) routes.push(`/clusters/${encodeURIComponent(ids.clusterId)}`);
  if (ids.entityName) routes.push(`/entity/${encodeURIComponent(ids.entityName)}`);
  if (ids.arcId) routes.push(`/narratives/${encodeURIComponent(ids.arcId)}`);
  if (ids.storyId) routes.push(`/story/${encodeURIComponent(ids.storyId)}`);
  if (ids.topic) routes.push(`/topic/${encodeURIComponent(ids.topic)}`);

  for (const route of routes) {
    await assertRouteHealthy(page, route);
  }
});
