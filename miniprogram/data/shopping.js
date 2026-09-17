const cloud = require('./cloud');
const PENDING = 'family-recipes.shopping.pending.v1';
let sharedSnapshot = [];
const KEY = 'family-recipes.shopping.v1';

function readLocalItems() {
  const value = wx.getStorageSync(KEY);
  if (value === '' || value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.some((item) => !item || typeof item.id !== 'string' || typeof item.name !== 'string' || typeof item.amount !== 'string' || typeof item.done !== 'boolean' || !Array.isArray(item.sources))) {
    throw new Error('无法读取买菜清单，请勿清理缓存，先联系开发者检查。');
  }
  return value;
}

async function readItems() {
  if (!cloud.enabled()) return readLocalItems();
  sharedSnapshot = await cloud.list('shopping');
  return sharedSnapshot;
}

async function commitShared(signature, makeChanges) {
  const pending = wx.getStorageSync(PENDING);
  if (pending) {
    try { await cloud.call('/api/shared/shopping', pending.payload); }
    catch (error) {
      if (error.status === 409) wx.removeStorageSync(PENDING);
      throw error;
    }
    wx.removeStorageSync(PENDING);
    if (pending.signature === signature) return;
  }
  const changes = await makeChanges();
  const payload = { operationId: 'op-' + Date.now() + '-' + Math.random().toString(36).slice(2), changes };
  wx.setStorageSync(PENDING, { signature, payload });
  try { await cloud.call('/api/shared/shopping', payload); }
  catch (error) {
    if (error.status === 409) wx.removeStorageSync(PENDING);
    throw error;
  }
  wx.removeStorageSync(PENDING);
}

// 只合并常见单位及最多三位小数，不推断“少许”、范围或单位换算。
function parseAmount(text) {
  const match = text.trim().match(/^(\d+(?:\.\d{1,3})?)\s*(个|克|千克|公斤|毫升|升|斤|两|颗|瓣|根|袋|盒|包|瓶)$/);
  if (!match) return null;
  const parts = match[1].split('.');
  const scaled = Number(parts[0]) * 1000 + Number(((parts[1] || '') + '000').slice(0, 3));
  if (!Number.isSafeInteger(scaled) || scaled <= 0) return null;
  return { scaled, unit: match[2] };
}

function mergeItems(items, ingredients, source) {
  if (!ingredients.length) throw new Error('请至少选择一项食材。');
  ingredients.forEach((ingredient, index) => {
    const name = ingredient.name.trim();
    const amount = ingredient.amount.trim() || '未注明';
    if (!name) throw new Error('请填写食材名称。');
    const parsed = parseAmount(amount);
    const target = parsed && items.find((item) => {
      const current = parseAmount(item.amount);
      return !item.done && item.name === name && current && current.unit === parsed.unit && Number.isSafeInteger(current.scaled + parsed.scaled);
    });
    if (target) {
      target.amount = ((parseAmount(target.amount).scaled + parsed.scaled) / 1000) + ' ' + parsed.unit;
      if (!target.sources.includes(source)) target.sources.push(source);
    } else {
      items.push({ id: 'buy-' + Date.now() + '-' + index + '-' + Math.random().toString(36).slice(2, 10), name, amount, done: false, sources: [source] });
    }
  });
  return items;
}

async function addItems(ingredients, source) {
  if (!cloud.enabled()) {
    const items = mergeItems(readLocalItems(), ingredients, source);
    wx.setStorageSync(KEY, items);
    return items;
  }
  return commitShared(JSON.stringify(['add', ingredients, source]), async () => {
    const original = await readItems();
    const items = mergeItems(JSON.parse(JSON.stringify(original)), ingredients, source);
    return items.filter((item) => JSON.stringify(item) !== JSON.stringify(original.find((r) => r.id === item.id)))
      .map((item) => Object.assign({}, item, { version: item.version || 0 }));
  });
}

async function toggleItem(id) {
  if (cloud.enabled()) {
    return commitShared('toggle:' + id, async () => {
      const item = sharedSnapshot.find((r) => r.id === id);
      if (!item) throw new Error('请刷新清单后再操作。');
      return [Object.assign({}, item, { done: !item.done })];
    });
  }
  const items = readLocalItems();
  const item = items.find((entry) => entry.id === id);
  if (!item) throw new Error('这项食材已不存在，请刷新清单。');
  item.done = !item.done;
  wx.setStorageSync(KEY, items);
}

async function removeItem(id) {
  if (cloud.enabled()) {
    return commitShared('delete:' + id, async () => {
      const item = sharedSnapshot.find((r) => r.id === id);
      if (!item) throw new Error('请刷新清单后再操作。');
      return [{ id, version: item.version, delete: true }];
    });
  }
  wx.setStorageSync(KEY, readLocalItems().filter((item) => item.id !== id));
}
async function migrateLocal() {
  const local = readLocalItems();
  let count = 0;
  for (const item of local) {
    const existing = await readItems();
    if (existing.some((r) => r.id === item.id)) continue;
    await commitShared('migrate:' + item.id, async () => [Object.assign({}, item, { version: 0 })]);
    count++;
  }
  return count;
}
function clearLocal() { wx.removeStorageSync(KEY); wx.removeStorageSync(PENDING); }
module.exports = { readItems, readLocalItems, parseAmount, addItems, toggleItem, removeItem, migrateLocal, clearLocal };
