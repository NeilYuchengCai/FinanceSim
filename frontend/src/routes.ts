/**
 * 动态导入映射 - 用于路由懒加载
 */

// 小页面 - 可预加载
export const lazySmallPages = {
  Overview: () => import('./pages/Overview'),
  Markets: () => import('./pages/Markets'),
  Equities: () => import('./pages/Equities'),
  Settings: () => import('./pages/Settings'),
  Simulation: () => import('./pages/Simulation'),
}

// 中等页面 - 按需加载
export const lazyMediumPages = {
  FX: () => import('./pages/FX'),
  Bonds: () => import('./pages/Bonds'),
  Portfolio: () => import('./pages/Portfolio'),
  Search: () => import('./pages/Search'),
  Analytics: () => import('./pages/Analytics'),
  News: () => import('./pages/News'),
  Commodities: () => import('./pages/Commodities'),
}

// 大页面 - 严格懒加载
export const lazyLargePages = {
  Orders: () => import('./pages/Orders'),
  Economy: () => import('./pages/Economy'),
  Bots: () => import('./pages/Bots'),
  Challenges: () => import('./pages/Challenges'),
  Timeline: () => import('./pages/Timeline'),
  WorldCreator: () => import('./pages/WorldCreator'),
}

// 合并所有路由
export const allLazyRoutes = {
  ...lazySmallPages,
  ...lazyMediumPages,
  ...lazyLargePages,
}
