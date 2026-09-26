import { useSyncExternalStore } from 'react'

/**
 * 中文翻译字典 - 完整版
 */
export const zhCN = {
  // 导航
  nav: {
    overview: '概览',
    markets: '市场',
    equities: '股票',
    fx: '外汇',
    bonds: '债券',
    commodities: '商品',
    bots: 'AI交易员',
    timeline: '时间线',
    portfolio: '投资组合',
    orders: '订单',
    news: '新闻',
    search: '搜索',
    analytics: '分析',
    economy: '宏观经济',
    simulation: '模拟',
    challenges: '挑战',
    settings: '设置',
    createWorld: '创建世界',
  },
  
  // 通用
  common: {
    loading: '加载中...',
    error: '错误',
    success: '成功',
    confirm: '确认',
    cancel: '取消',
    save: '保存',
    delete: '删除',
    edit: '编辑',
    refresh: '刷新',
    close: '关闭',
    back: '返回',
    next: '下一步',
    previous: '上一步',
    submit: '提交',
    reset: '重置',
    search: '搜索...',
    filter: '筛选',
    sort: '排序',
    all: '全部',
    none: '无',
    unknown: '未知',
    noData: '暂无数据',
    dataError: '数据加载失败',
    networkError: '网络连接失败',
    retry: '重试',
  },
  
  // 概览
  overview: {
    title: '市场概览',
    subtitle: '全球金融市场一览',
    gdp: 'GDP增长',
    inflation: '通胀率',
    unemployment: '失业率',
    interestRate: '利率',
    centralBank: '中央银行',
    policy: '货币政策',
    breakingNews: '突发新闻',
    importantNews: '重要新闻',
    marketSentiment: '市场情绪',
    bullish: '看涨',
    bearish: '看跌',
    neutral: '中性',
  },
  
  // 市场
  markets: {
    title: '市场概览',
    subtitle: '指数行情、市场广度与板块表现',
    summary: '市场摘要',
    topGainers: '涨幅榜',
    topLosers: '跌幅榜',
    mostActive: '活跃榜',
    bySector: '按板块',
    byExchange: '按交易所',
    marketBreadth: '市场广度',
    code: '代码',
    name: '名称',
    price: '现价',
    change: '涨跌幅',
    volume: '成交量',
    advancing: '上涨家数',
    declining: '下跌家数',
    unchanged: '持平',
    ofTotal: '占比',
    adLine: '腾落线 A-D',
    adRatio: '涨跌比',
    avgChange: '平均涨跌',
    newHighLow: '新高/新低',
    distribution: '涨跌幅分布',
    instruments: '只标的',
    sectors: '板块表现',
    sector: '板块',
    count: '数量',
    gainers: '涨幅榜',
    losers: '跌幅榜',
    globalIndices: '全球主要指数',
  },
  
  // 股票
  equities: {
    title: '股票市场',
    subtitle: '股票市场概览和交易',
    searchStock: '搜索股票代码或名称...',
    fundamentals: '基本面',
    technicals: '技术面',
    news: '相关新闻',
    orderBook: '订单簿',
    buy: '买入',
    sell: '卖出',
    hold: '持有',
    ticker: '代码',
    name: '名称',
    price: '价格',
    change: '涨跌',
    volume: '成交量',
    marketCap: '市值',
    pe: '市盈率',
    sector: '板块',
    exchange: '交易所',
  },
  
  // 外汇
  fx: {
    title: '外汇市场',
    subtitle: '货币对实时汇率',
    pairs: '货币对',
    bid: '买入价',
    ask: '卖出价',
    spread: '点差',
    change: '涨跌幅',
    high: '最高',
    low: '最低',
    volume: '成交量',
    usdCny: '美元/人民币',
    eurUsd: '欧元/美元',
    gbpUsd: '英镑/美元',
    usdChf: '美元/瑞郎',
  },
  
  // 债券
  bonds: {
    title: '债券市场',
    subtitle: '国债和企业债',
    yieldCurve: '收益率曲线',
    duration: '久期',
    convexity: '凸性',
    coupon: '票息',
    maturity: '到期',
    rating: '评级',
    treasury: '国债',
    corporate: '企业债',
    yield: '收益率',
  },
  
  // 商品
  commodities: {
    title: '商品市场',
    subtitle: '大宗商品交易',
    energy: '能源',
    metals: '金属',
    agriculture: '农产品',
    precious: '贵金属',
    supplyDemand: '供需关系',
    inventory: '库存',
    crudeOil: '原油',
    gold: '黄金',
    silver: '白银',
    copper: '铜',
    wheat: '小麦',
  },
  
  // 宏观经济
  economy: {
    title: '宏观经济',
    subtitle: '经济指标和趋势',
    gdp: 'GDP',
    cpi: 'CPI',
    ppi: 'PPI',
    unemployment: '失业率',
    interestRate: '利率',
    moneySupply: '货币供应量',
    centralBank: '中央银行',
    policy: '货币政策',
    nextReview: '下次审查',
    fiscalPolicy: '财政政策',
    governmentDebt: '政府债务',
    tradeBalance: '贸易差额',
  },
  
  // AI交易员
  bots: {
    title: 'AI交易员',
    subtitle: '智能交易策略',
    value: '价值投资',
    growth: '成长投资',
    macro: '宏观策略',
    pairs: '配对交易',
    performance: '表现',
    wins: '胜率',
    trades: '交易次数',
    profitLoss: '盈亏',
    drawdown: '回撤',
    sharpe: '夏普比率',
  },
  
  // 投资组合
  portfolio: {
    title: '投资组合',
    subtitle: '资产管理和绩效分析',
    totalValue: '总资产',
    todayChange: '今日涨跌',
    totalReturn: '总收益率',
    allocation: '资产配置',
    positions: '持仓',
    availableCash: '可用资金',
    realizedPnl: '已实现盈亏',
    unrealizedPnl: '未实现盈亏',
  },
  
  // 订单
  orders: {
    title: '订单管理',
    subtitle: '查看和管理交易订单',
    openOrders: '挂单',
    filledOrders: '已成交',
    pendingOrders: '待成交',
    cancelOrders: '已取消',
    orderType: '订单类型',
    market: '市价',
    limit: '限价',
    stop: '止损',
    quantity: '数量',
    price: '价格',
    status: '状态',
  },
  
  // 新闻
  news: {
    title: '新闻',
    subtitle: '市场新闻和事件',
    breaking: '突发新闻',
    important: '重要',
    normal: '一般',
    market: '市场',
    economy: '经济',
    company: '公司',
    policy: '政策',
    technology: '科技',
  },
  
  // 时间线
  timeline: {
    title: '时间线',
    subtitle: '市场历史事件记录',
    events: '事件',
    filters: '筛选',
    dateRange: '日期范围',
    eventTypes: '事件类型',
    marketEvent: '市场事件',
    economicEvent: '经济事件',
    corporateEvent: '公司事件',
  },
  
  // 分析
  analytics: {
    title: '分析',
    subtitle: '深度数据分析',
    performance: '绩效分析',
    risk: '风险分析',
    correlation: '相关性',
    distribution: '分布',
    volatility: '波动率',
    beta: 'Beta值',
    alpha: 'Alpha值',
    returnsAnalysis: '收益分析',
    riskMetrics: '风险指标',
    correlationMatrix: '相关性矩阵',
    drawdownAnalysis: '回撤分析',
    selectAsset: '选择标的',
    asset: '标的',
    sampleDays: '样本天数',
    cumulativeReturn: '累计收益率',
    totalReturn: '区间总收益率',
    annualizedReturn: '年化收益率',
    annualizedVolatility: '年化波动率',
    sharpeRatio: '夏普比率',
    maxDrawdown: '最大回撤',
    maxDrawdownDate: '发生日期',
    var95: '95% 单日 VaR',
    positiveDays: '正收益天数占比',
    riskFreeRate: '无风险利率',
    underwaterCurve: '水下曲线',
    drawdownPct: '回撤',
  },
  
  // 模拟
  simulation: {
    title: '模拟设置',
    subtitle: '配置模拟参数',
    speed: '模拟速度',
    startDate: '开始日期',
    endDate: '结束日期',
    seed: '随机种子',
    run: '运行',
    pause: '暂停',
    reset: '重置',
    realTime: '实时',
    fastForward: '快进',
    // Simulation page keys
    actionFailed: '操作失败',
    controls: '模拟控制',
    cyclePhase: '周期阶段',
    dayPrefix: '第',
    eventTime: '时间',
    eventTitle: '事件',
    eventType: '类型',
    gdpGrowth: 'GDP 增速',
    inflation: '通胀率',
    interestRate: '利率',
    marketStatus: '市场状态',
    metric: '指标',
    nextTradingDay: '下一个交易日',
    nonTradingDay: '非交易日',
    paused: '已暂停',
    play: '播放',
    running: '运行中',
    severity: '强度',
    simTime: '模拟时间',
    step: '执行一步',
    todayEvents: '今日事件',
    tradingDay: '交易日',
    unemployment: '失业率',
  },
  
  // 挑战
  challenges: {
    title: '挑战模式',
    subtitle: '完成指定投资目标',
    beginner: '新手挑战',
    intermediate: '进阶挑战',
    expert: '专家挑战',
    completed: '已完成',
    inProgress: '进行中',
    available: '可用',
    progress: '进度',
    reward: '奖励',
  },
  
  // 设置
  settings: {
    title: '设置',
    subtitle: '自定义应用选项',
    language: '语言',
    chinese: '简体中文',
    english: 'English',
    theme: '主题',
    dark: '深色模式',
    light: '浅色模式',
    notifications: '通知设置',
    sound: '音效',
    soundOn: '开启音效',
    soundOff: '关闭音效',
    dataSources: '数据源',
    offlineMode: '离线模式',
    autoSave: '自动保存',
    general: '通用设置',
    simulation: '模拟设置',
    currencyDisplay: '货币显示',
    defaultSpeed: '默认速度',
    dataSource: '数据源',
    fallback: '内置数据',
    saved: '设置已保存',
    preview: '预览',
  },
  
  // 搜索
  search: {
    title: '全局搜索',
    subtitle: '搜索资产、新闻、事件',
    placeholder: '输入关键词搜索...',
    assets: '资产',
    news: '新闻',
    events: '事件',
    results: '搜索结果',
    noResults: '未找到相关结果',
  },
  
  // 世界管理
  world: {
    title: '世界管理',
    createWorld: '创建世界',
    restoreWorld: '还原世界',
    branchWorld: '分支世界',
    snapshot: '世界快照',
    name: '名称',
    description: '描述',
    mode: '模式',
    demo: '演示模式',
    sandbox: '沙盒模式',
    competitive: '竞技模式',
    seed: '随机种子',
  },
};

/**
 * English translation dictionary - mirrors zhCN structure key by key
 */
export const enUS = {
  nav: {
    overview: 'Overview',
    markets: 'Markets',
    equities: 'Equities',
    fx: 'FX',
    bonds: 'Bonds',
    commodities: 'Commodities',
    bots: 'AI Traders',
    timeline: 'Timeline',
    portfolio: 'Portfolio',
    orders: 'Orders',
    news: 'News',
    search: 'Search',
    analytics: 'Analytics',
    economy: 'Economy',
    simulation: 'Simulation',
    challenges: 'Challenges',
    settings: 'Settings',
    createWorld: 'Create World',
  },

  common: {
    loading: 'Loading...',
    error: 'Error',
    success: 'Success',
    confirm: 'Confirm',
    cancel: 'Cancel',
    save: 'Save',
    delete: 'Delete',
    edit: 'Edit',
    refresh: 'Refresh',
    close: 'Close',
    back: 'Back',
    next: 'Next',
    previous: 'Previous',
    submit: 'Submit',
    reset: 'Reset',
    search: 'Search...',
    filter: 'Filter',
    sort: 'Sort',
    all: 'All',
    none: 'None',
    unknown: 'Unknown',
    noData: 'No data',
    dataError: 'Failed to load data',
    networkError: 'Network connection failed',
    retry: 'Retry',
  },

  overview: {
    title: 'Market Overview',
    subtitle: 'A glance at global financial markets',
    gdp: 'GDP Growth',
    inflation: 'Inflation',
    unemployment: 'Unemployment',
    interestRate: 'Interest Rate',
    centralBank: 'Central Bank',
    policy: 'Monetary Policy',
    breakingNews: 'Breaking News',
    importantNews: 'Important News',
    marketSentiment: 'Market Sentiment',
    bullish: 'Bullish',
    bearish: 'Bearish',
    neutral: 'Neutral',
  },

  markets: {
    title: 'Market Overview',
    subtitle: 'Indices, market breadth and sector performance',
    summary: 'Market Summary',
    topGainers: 'Top Gainers',
    topLosers: 'Top Losers',
    mostActive: 'Most Active',
    bySector: 'By Sector',
    byExchange: 'By Exchange',
    marketBreadth: 'Market Breadth',
    code: 'Code',
    name: 'Name',
    price: 'Price',
    change: 'Change',
    volume: 'Volume',
    advancing: 'Advancing',
    declining: 'Declining',
    unchanged: 'Unchanged',
    ofTotal: 'Of Total',
    adLine: 'A-D Line',
    adRatio: 'Advance/Decline Ratio',
    avgChange: 'Average Change',
    newHighLow: 'New Highs / Lows',
    distribution: 'Change Distribution',
    instruments: 'instruments',
    sectors: 'Sector Performance',
    sector: 'Sector',
    count: 'Count',
    gainers: 'Gainers',
    losers: 'Losers',
    globalIndices: 'Global Indices',
  },

  equities: {
    title: 'Equity Market',
    subtitle: 'Equity market overview and trading',
    searchStock: 'Search ticker or company name...',
    fundamentals: 'Fundamentals',
    technicals: 'Technicals',
    news: 'Related News',
    orderBook: 'Order Book',
    buy: 'Buy',
    sell: 'Sell',
    hold: 'Hold',
    ticker: 'Ticker',
    name: 'Name',
    price: 'Price',
    change: 'Change',
    volume: 'Volume',
    marketCap: 'Market Cap',
    pe: 'P/E Ratio',
    sector: 'Sector',
    exchange: 'Exchange',
  },

  fx: {
    title: 'FX Market',
    subtitle: 'Live currency pair rates',
    pairs: 'Pairs',
    bid: 'Bid',
    ask: 'Ask',
    spread: 'Spread',
    change: 'Change',
    high: 'High',
    low: 'Low',
    volume: 'Volume',
    usdCny: 'USD/CNY',
    eurUsd: 'EUR/USD',
    gbpUsd: 'GBP/USD',
    usdChf: 'USD/CHF',
  },

  bonds: {
    title: 'Bond Market',
    subtitle: 'Government and corporate bonds',
    yieldCurve: 'Yield Curve',
    duration: 'Duration',
    convexity: 'Convexity',
    coupon: 'Coupon',
    maturity: 'Maturity',
    rating: 'Rating',
    treasury: 'Treasury',
    corporate: 'Corporate',
    yield: 'Yield',
  },

  commodities: {
    title: 'Commodities',
    subtitle: 'Commodity trading',
    energy: 'Energy',
    metals: 'Metals',
    agriculture: 'Agriculture',
    precious: 'Precious Metals',
    supplyDemand: 'Supply & Demand',
    inventory: 'Inventory',
    crudeOil: 'Crude Oil',
    gold: 'Gold',
    silver: 'Silver',
    copper: 'Copper',
    wheat: 'Wheat',
  },

  economy: {
    title: 'Macro Economy',
    subtitle: 'Economic indicators and trends',
    gdp: 'GDP',
    cpi: 'CPI',
    ppi: 'PPI',
    unemployment: 'Unemployment',
    interestRate: 'Interest Rate',
    moneySupply: 'Money Supply',
    centralBank: 'Central Bank',
    policy: 'Monetary Policy',
    nextReview: 'Next Review',
    fiscalPolicy: 'Fiscal Policy',
    governmentDebt: 'Government Debt',
    tradeBalance: 'Trade Balance',
  },

  bots: {
    title: 'AI Traders',
    subtitle: 'Intelligent trading strategies',
    value: 'Value Investing',
    growth: 'Growth Investing',
    macro: 'Macro Strategy',
    pairs: 'Pairs Trading',
    performance: 'Performance',
    wins: 'Win Rate',
    trades: 'Trades',
    profitLoss: 'Profit / Loss',
    drawdown: 'Drawdown',
    sharpe: 'Sharpe Ratio',
  },

  portfolio: {
    title: 'Portfolio',
    subtitle: 'Asset management and performance',
    totalValue: 'Total Value',
    todayChange: 'Today Change',
    totalReturn: 'Total Return',
    allocation: 'Allocation',
    positions: 'Positions',
    availableCash: 'Available Cash',
    realizedPnl: 'Realized P&L',
    unrealizedPnl: 'Unrealized P&L',
  },

  orders: {
    title: 'Orders',
    subtitle: 'View and manage trade orders',
    openOrders: 'Open Orders',
    filledOrders: 'Filled',
    pendingOrders: 'Pending',
    cancelOrders: 'Cancelled',
    orderType: 'Order Type',
    market: 'Market',
    limit: 'Limit',
    stop: 'Stop',
    quantity: 'Quantity',
    price: 'Price',
    status: 'Status',
  },

  news: {
    title: 'News',
    subtitle: 'Market news and events',
    breaking: 'Breaking',
    important: 'Important',
    normal: 'Normal',
    market: 'Market',
    economy: 'Economy',
    company: 'Company',
    policy: 'Policy',
    technology: 'Technology',
  },

  timeline: {
    title: 'Timeline',
    subtitle: 'Historical market events',
    events: 'Events',
    filters: 'Filters',
    dateRange: 'Date Range',
    eventTypes: 'Event Types',
    marketEvent: 'Market Event',
    economicEvent: 'Economic Event',
    corporateEvent: 'Corporate Event',
  },

  analytics: {
    title: 'Analytics',
    subtitle: 'Deep data analysis',
    performance: 'Performance',
    risk: 'Risk',
    correlation: 'Correlation',
    distribution: 'Distribution',
    volatility: 'Volatility',
    beta: 'Beta',
    alpha: 'Alpha',
    returnsAnalysis: 'Returns Analysis',
    riskMetrics: 'Risk Metrics',
    correlationMatrix: 'Correlation Matrix',
    drawdownAnalysis: 'Drawdown Analysis',
    selectAsset: 'Select Asset',
    asset: 'Asset',
    sampleDays: 'Sample Days',
    cumulativeReturn: 'Cumulative Return',
    totalReturn: 'Period Total Return',
    annualizedReturn: 'Annualized Return',
    annualizedVolatility: 'Annualized Volatility',
    sharpeRatio: 'Sharpe Ratio',
    maxDrawdown: 'Max Drawdown',
    maxDrawdownDate: 'Date',
    var95: '95% 1-Day VaR',
    positiveDays: 'Positive Days',
    riskFreeRate: 'Risk-Free Rate',
    underwaterCurve: 'Underwater Curve',
    drawdownPct: 'Drawdown',
  },

  simulation: {
    title: 'Simulation Settings',
    subtitle: 'Configure simulation parameters',
    speed: 'Simulation Speed',
    startDate: 'Start Date',
    endDate: 'End Date',
    seed: 'Random Seed',
    run: 'Run',
    pause: 'Pause',
    reset: 'Reset',
    realTime: 'Real Time',
    fastForward: 'Fast Forward',
    // Simulation page keys
    actionFailed: 'Action failed',
    controls: 'Simulation Controls',
    cyclePhase: 'Cycle Phase',
    dayPrefix: 'Day',
    eventTime: 'Time',
    eventTitle: 'Event',
    eventType: 'Type',
    gdpGrowth: 'GDP Growth',
    inflation: 'Inflation Rate',
    interestRate: 'Interest Rate',
    marketStatus: 'Market Status',
    metric: 'Metric',
    nextTradingDay: 'Next Trading Day',
    nonTradingDay: 'Non-Trading Day',
    paused: 'Paused',
    play: 'Play',
    running: 'Running',
    severity: 'Severity',
    simTime: 'Sim Time',
    step: 'Step',
    todayEvents: 'Today Events',
    tradingDay: 'Trading Day',
    unemployment: 'Unemployment',
  },

  challenges: {
    title: 'Challenges',
    subtitle: 'Complete investment objectives',
    beginner: 'Beginner',
    intermediate: 'Intermediate',
    expert: 'Expert',
    completed: 'Completed',
    inProgress: 'In Progress',
    available: 'Available',
    progress: 'Progress',
    reward: 'Reward',
  },

  settings: {
    title: 'Settings',
    subtitle: 'Customize application options',
    language: 'Language',
    chinese: '简体中文',
    english: 'English',
    theme: 'Theme',
    dark: 'Dark Mode',
    light: 'Light Mode',
    notifications: 'Notifications',
    sound: 'Sound',
    soundOn: 'Sound On',
    soundOff: 'Sound Off',
    dataSources: 'Data Sources',
    offlineMode: 'Offline Mode',
    autoSave: 'Auto Save',
    general: 'General',
    simulation: 'Simulation',
    currencyDisplay: 'Currency Display',
    defaultSpeed: 'Default Speed',
    dataSource: 'Data Source',
    fallback: 'Built-in Data',
    saved: 'Settings saved',
    preview: 'Preview',
  },

  search: {
    title: 'Global Search',
    subtitle: 'Search assets, news and events',
    placeholder: 'Type keywords to search...',
    assets: 'Assets',
    news: 'News',
    events: 'Events',
    results: 'Results',
    noResults: 'No results found',
  },

  world: {
    title: 'World Management',
    createWorld: 'Create World',
    restoreWorld: 'Restore World',
    branchWorld: 'Branch World',
    snapshot: 'World Snapshot',
    name: 'Name',
    description: 'Description',
    mode: 'Mode',
    demo: 'Demo Mode',
    sandbox: 'Sandbox Mode',
    competitive: 'Competitive Mode',
    seed: 'Random Seed',
  },
};

/* ------------------------------------------------------------------ *
 * Runtime language switching
 * ------------------------------------------------------------------ */

export type LanguageCode = 'zh' | 'en'

export const LANG_STORAGE_KEY = 'financesim-lang'

const DICTIONARIES: Record<LanguageCode, Record<string, any>> = {
  zh: zhCN as unknown as Record<string, any>,
  en: enUS as unknown as Record<string, any>,
}

const LANGUAGE_LOCALES: Record<LanguageCode, string> = {
  zh: 'zh-CN',
  en: 'en-US',
}

function readStoredLanguage(): LanguageCode {
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY)
    if (saved === 'zh' || saved === 'en') return saved
  } catch {
    /* localStorage unavailable (SSR / private mode) - fall through */
  }
  return 'zh'
}

let currentLanguage: LanguageCode = readStoredLanguage()
const languageListeners = new Set<() => void>()

export function getLanguage(): LanguageCode {
  return currentLanguage
}

export function setLanguage(lang: LanguageCode): void {
  if (lang !== 'zh' && lang !== 'en') return
  if (lang === currentLanguage) return
  currentLanguage = lang
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang)
    document.documentElement.setAttribute('lang', LANGUAGE_LOCALES[lang])
  } catch {
    /* ignore storage errors - language still switches in memory */
  }
  languageListeners.forEach(listener => listener())
}

function subscribeLanguage(listener: () => void): () => void {
  languageListeners.add(listener)
  return () => {
    languageListeners.delete(listener)
  }
}

/**
 * Subscribe to language changes so the calling component re-renders.
 */
export function useLanguage(): { language: LanguageCode; setLanguage: (lang: LanguageCode) => void } {
  const language = useSyncExternalStore(subscribeLanguage, getLanguage, () => 'zh' as LanguageCode)
  return { language, setLanguage }
}

/**
 * 获取翻译文本的辅助函数
 */
export function t(key: string, fallback?: string): string {
  const keys = key.split('.')
  const dict = DICTIONARIES[currentLanguage] || DICTIONARIES.zh

  let obj: any = dict

  for (const k of keys) {
    if (obj && obj[k] !== undefined) {
      obj = obj[k]
    } else {
      return fallback || key
    }
  }

  return typeof obj === 'string' ? obj : fallback || key
}

/* ------------------------------------------------------------------ *
 * Currency formatting (driven by Settings -> Currency Display)
 * ------------------------------------------------------------------ */

export type CurrencyCode = 'USD' | 'EUR' | 'CNY' | 'CHF'

export const CURRENCIES: { code: CurrencyCode; symbol: string }[] = [
  { code: 'USD', symbol: '$' },
  { code: 'EUR', symbol: '€' },
  { code: 'CNY', symbol: '¥' },
  { code: 'CHF', symbol: 'Fr' },
]

export function isCurrencyCode(value: unknown): value is CurrencyCode {
  return value === 'USD' || value === 'EUR' || value === 'CNY' || value === 'CHF'
}

export function formatCurrency(value: number, currency: CurrencyCode = 'USD', language?: LanguageCode): string {
  const amount = Number.isFinite(value) ? value : 0
  const locale = LANGUAGE_LOCALES[language || currentLanguage]
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    const symbol = CURRENCIES.find(c => c.code === currency)?.symbol || currency
    return `${symbol}${amount.toFixed(2)}`
  }
}
