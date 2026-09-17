Page({
  data: { query: '', results: [], displayResults: [], page: 0, totalPages: 0, searched: false, busy: false, activeId: '', error: '', draft: null, warnings: [] },
  onInput(event) { this.setData({ query: event.detail.value, results: [], searched: false, draft: null, error: '' }); },
  onUnload() { this.closed = true; if (this.request) this.request.abort(); },
  call(path, data, success) {
    this.setData({ busy: true, error: '' });
    this.request = require('../../data/cloud').transport({
      url: 'http://127.0.0.1:8765' + path, method: 'POST', timeout: 90000,
      header: { 'content-type': 'application/json', 'X-Recipe-Client': 'local-miniprogram' }, data,
      success: (response) => {
        if (this.closed) return;
        if (response.statusCode !== 200) {
          this.setData({ error: response.statusCode === 404 ? '请重启本地 Python 后端以启用搜索接口。' : (response.data || {}).error || '请求失败，请重试。' }); return;
        }
        success(response.data);
      },
      fail: () => { if (!this.closed) this.setData({ error: '连接失败或超时，请检查网络和服务配置。没有自动重试。' }); },
      complete: () => { if (!this.closed) this.setData({ busy: false, activeId: '' }); }
    });
  },
  onSearch() {
    if (this.data.busy) return;
    if (!this.data.query.trim()) { this.setData({ error: '请输入菜名，如红烧肉。' }); return; }
    this.setData({ results: [], draft: null, searched: false });
    this.call('/api/search-recipes', { query: this.data.query.trim() }, (body) => this.setData({ results: body.results || [], displayResults: (body.results || []).slice(0, 5), page: 0, totalPages: Math.max(1, Math.ceil((body.results || []).length / 5)), searched: true }));
  },
  onNextPage() { const page = this.data.page + 1; this.setData({ page, displayResults: this.data.results.slice(page * 5, page * 5 + 5) }); },
  onPrevPage() { const page = Math.max(0, this.data.page - 1); this.setData({ page, displayResults: this.data.results.slice(page * 5, page * 5 + 5) }); },
  onChoose(event) {
    if (this.data.busy) return;
    const id = event.currentTarget.dataset.id;
    this.setData({ activeId: id, draft: null });
    this.call('/api/organize-candidate', { candidateId: id }, (body) => {
      if (!body.draft) { this.setData({ error: '没有得到完整草稿，请选择其他来源。' }); return; }
      this.setData({ draft: body.draft, warnings: body.warnings || [] });
      this.onEdit();
    });
  },
  onEdit() {
    if (!this.data.draft) return;
    wx.navigateTo({ url: '/pages/editor/index?imported=1', success: (result) => result.eventChannel.emit('importDraft', { draft: this.data.draft, warnings: this.data.warnings }), fail: () => this.setData({ error: '草稿已准备好，请点击继续编辑。' }) });
  },
  onCopy(event) { wx.setClipboardData({ data: event.currentTarget.dataset.url }); },
  onPaste() { wx.navigateTo({ url: '/pages/paste/index' }); }
});
