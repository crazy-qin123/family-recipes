// 学习用演示内容，由本项目编写；不是从下厨房抓取的正式菜谱库。
const recipes = [
  {
    id: 'tomato-eggs', name: '番茄炒蛋', category: '家常菜', symbol: '🍅',
    summary: '酸甜开胃，把熟悉的家常味留在这里。', servings: '2 人份', time: '约 15 分钟',
    ingredients: [{ name: '番茄', amount: '2 个' }, { name: '鸡蛋', amount: '3 个' }, { name: '食用油', amount: '适量' }, { name: '盐', amount: '适量' }],
    steps: ['番茄洗净切块，鸡蛋打入碗中充分搅匀。', '锅中加油烧热，倒入蛋液炒至凝固后盛出。', '锅中补少量油，加入番茄翻炒出汁，必要时加少量水。', '倒回鸡蛋，翻炒至全部熟透，加盐调味后盛出。'],
    note: '可在正式录入时补充家人喜欢的酸甜程度。'
  },
  {
    id: 'stir-fried-broccoli', name: '清炒西兰花', category: '家常菜', symbol: '🥦',
    summary: '简单清爽，搭配一碗米饭或一道主菜。', servings: '2 人份', time: '约 15 分钟',
    ingredients: [{ name: '西兰花', amount: '1 颗' }, { name: '蒜', amount: '2 瓣' }, { name: '食用油', amount: '适量' }, { name: '盐', amount: '适量' }],
    steps: ['西兰花切成小朵洗净，蒜切碎。', '西兰花放入沸水中焯至接近熟透，捞出沥水。', '锅中放油，加入蒜末炒香。', '放入西兰花翻炒，加盐调味，炒至熟透且达到喜欢的软硬程度。'],
    note: '软硬程度可以按家庭口味调整。'
  },
  {
    id: 'potato-strips', name: '醋溜土豆丝', category: '家常菜', symbol: '🥔',
    summary: '食材常见，清爽下饭的一道日常小菜。', servings: '2 人份', time: '约 20 分钟',
    ingredients: [{ name: '土豆', amount: '2 个' }, { name: '蒜', amount: '2 瓣' }, { name: '醋', amount: '适量' }, { name: '食用油', amount: '适量' }, { name: '盐', amount: '适量' }],
    steps: ['土豆去皮切丝，用清水冲洗后沥干，蒜切碎。', '热锅放油，加入蒜末炒香。', '加入土豆丝翻炒，可加少量水防止粘锅。', '炒至熟透，加入盐和醋调味后出锅。'],
    note: '喜欢辣味时可在自家版本中添加辣椒。'
  },
  {
    id: 'seaweed-egg-soup', name: '紫菜蛋花汤', category: '汤羹', symbol: '🥣',
    summary: '一碗热汤，为家常饭补上最后一笔。', servings: '2 人份', time: '约 10 分钟',
    ingredients: [{ name: '紫菜', amount: '适量' }, { name: '鸡蛋', amount: '1 个' }, { name: '水', amount: '600 毫升' }, { name: '盐', amount: '适量' }],
    steps: ['按紫菜包装说明处理紫菜，鸡蛋打散。', '锅中水烧开，放入紫菜煮开。', '保持汤沸腾，缓缓倒入蛋液，待蛋花凝固并熟透。', '加盐调味后盛出。'],
    note: '可在家庭备注里记录喜欢的配料。'
  }
];

const categories = ['全部', '家常菜', '凉菜', '主食', '早餐', '海鲜', '汤羹', '地方特色菜'];

function searchRecipes(keyword, category) {
  const query = (keyword || '').trim().toLowerCase();
  return recipes.filter((recipe) => {
    const matchesCategory = !category || category === '全部' || recipe.category === category;
    const searchable = [recipe.name].concat(recipe.ingredients.map((item) => item.name)).join(' ').toLowerCase();
    return matchesCategory && searchable.includes(query);
  });
}

function getRecipe(id) {
  return recipes.find((recipe) => recipe.id === id) || null;
}

module.exports = { recipes, categories, searchRecipes, getRecipe };
