import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// Bonds API —— 仅保留页面实际调用的部分（收益率曲线）。
// 其余未使用的导出（assetsApi / fxApi / commoditiesApi / economyApi /
// newsApi / worldApi 及其接口）已按死代码清理移除。
export const bondsApi = {
  getYieldCurve: async () => {
    const res = await api.get('/bonds/yield-curve')
    return res.data
  },
}

export default api
