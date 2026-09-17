Page({
  data: { text: '', busy: false, error: '', draft: null, warnings: [] },
  onInput(event) { this.setData({ text: event.detail.value, error: '', draft: null }); },
  onUnload() { this.closed = true; if (this.request) this.request.abort(); },
  onOrganize() {
    if (this.data.busy) return;
    const input = this.data.text.trim();
    const isUrl = /^https:\/\/[^\s]+$/i.test(input);
    if (input.length < 10) { this.setData({ error: '请粘贴菜谱正文或完整的 HTTPS 菜谱链接。' }); return; }
    this.setData({ busy: true, draft: null, error: '' });
    this.request = require('../../data/cloud').transport({
      url: 'http://127.0.0.1:8765' + (isUrl ? '/api/organize-url' : '/api/organize-text'), method: 'POST', timeout: 90000,
      header: { 'content-type': 'application/json', 'X-Recipe-Client': 'local-miniprogram' },
      data: isUrl ? { url: input } : { text: input },
      success: (response) => {
        if (this.closed) return;
        const body = response.data || {};
        if (response.statusCode !== 200 || !body.draft) {
          this.setData({ error: response.statusCode === 404 ? '后端还是旧版本，请重启 Python 服务。' : body.error || '整理失败，原文已保留。' }); return;
        }
        this.setData({ draft: body.draft, warnings: body.warnings || [] });
        this.onEdit();
      },
      fail: () => { if (!this.closed) this.setData({ error: '连接失败或超时，请检查网络和服务配置。原文已保留。' }); },
      complete: () => { if (!this.closed) this.setData({ busy: false }); }
    });
  },
  onEdit() {
    if (!this.data.draft) return;
    wx.navigateTo({ url: '/pages/editor/index?imported=1', success: (result) => result.eventChannel.emit('importDraft', { draft: this.data.draft, warnings: this.data.warnings }), fail: () => this.setData({ error: '草稿已准备好，请点击继续编辑。' }) });
  }
});
