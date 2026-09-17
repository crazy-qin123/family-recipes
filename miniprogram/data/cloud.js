const KEY = 'family-recipes.connection.v1';
const ENV = 'family-yan-d3ggl5qqu3f0cf916';
const SERVICE = 'family-recipes-api';
function settings() { return wx.getStorageSync(KEY) || {}; }
function enabled() { return settings().enabled === true; }
function configure(token) {
  if (typeof token !== 'string' || !/^[\x21-\x7e]{32,}$/.test(token)) throw new Error('请填写完整的家庭访问凭证。');
  wx.setStorageSync(KEY, { enabled: true, token });
}
function disable() { wx.removeStorageSync(KEY); }
function transport(options) {
  if (!enabled()) return wx.request(options);
  const path = options.url.replace('http://127.0.0.1:8765', '');
  let cancelled = false;
  Promise.resolve().then(() => {
    if (!wx.cloud) throw new Error('当前微信版本不支持云开发，请升级微信。');
    wx.cloud.init({ env: ENV });
    return wx.cloud.callContainer({ config: { env: ENV }, path, method: options.method || 'POST',
      header: { 'content-type': 'application/json', 'X-WX-SERVICE': SERVICE,
        Authorization: 'Bearer ' + settings().token }, data: options.data, timeout: 90000 });
  }).then((result) => { if (!cancelled && options.success) options.success(result); },
    (error) => { if (!cancelled && options.fail) options.fail(error); })
    .finally(() => { if (!cancelled && options.complete) options.complete(); });
  return { abort() { cancelled = true; } };
}
function call(path, data) {
  return new Promise((resolve, reject) => {
    transport({ url: 'http://127.0.0.1:8765' + path, method: 'POST', data,
      success(result) {
        if (result.statusCode !== 200) {
          const error = new Error((result.data || {}).error || '共享服务请求失败');
          error.status = result.statusCode;
          reject(error);
        } else resolve(result.data);
      }, fail() { reject(new Error('连接失败或超时，请检查网络。保存结果可能尚未返回，请重试原操作。')); }
    });
  });
}
async function list(collection) {
  let offset = 0;
  const items = [];
  do {
    const result = await call('/api/shared/list', { collection, offset });
    items.push(...result.items);
    offset = result.nextOffset;
  } while (offset !== null);
  return items;
}
module.exports = { enabled, configure, disable, transport, call, list };
