Page({
  data: { url: '', busy: false, error: '', draft: null, warnings: [] },
  onUrl(event) { this.setData({ url: event.detail.value, draft: null, error: '', warnings: [] }); },
  onUnload() { this.closed = true; if (this.request) this.request.abort(); },
  onParse() {
    if (this.data.busy) return;
    if (!this.data.url.trim()) { this.setData({ error: '请先粘贴国内菜谱网站链接。' }); return; }
    this.setData({ busy: true, error: '', draft: null, warnings: [] });
    this.request = require('../../data/cloud').transport({
      url: 'http://127.0.0.1:8765/api/organize-url', method: 'POST', timeout: 90000,
      header: { 'content-type': 'application/json', 'X-Recipe-Client': 'local-miniprogram' },
      data: { url: this.data.url.trim() },
      success: (response) => {
        if (this.closed) return;
        const body = response.data || {};
        if (response.statusCode !== 200 || !body.draft) { this.setData({ error: body.error || '未能获取菜谱，请稍后重试。' }); return; }
        this.setData({ draft: body.draft, warnings: body.warnings || [] });
        this.onEdit();
      },
      fail: () => { if (!this.closed) this.setData({ error: '无法连接整理服务，请检查网络或改用粘贴正文。' }); },
      complete: () => { if (!this.closed) this.setData({ busy: false }); }
    });
  },
  onEdit() {
    if (!this.data.draft) return;
    wx.navigateTo({ url: '/pages/editor/index?imported=1', success: (result) => {
      result.eventChannel.emit('importDraft', { draft: this.data.draft, warnings: this.data.warnings });
    }, fail: () => this.setData({ error: '草稿已提取，打开表单失败，请点击继续编辑。' }) });
  },
  onManual() { wx.navigateTo({ url: '/pages/editor/index' }); }
});
