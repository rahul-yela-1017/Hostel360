import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 20000 })
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('hostel_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use(r => r, error => {
  if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
    localStorage.removeItem('hostel_token')
    localStorage.removeItem('hostel_user')
    window.dispatchEvent(new Event('hostel:unauthorized'))
  }
  return Promise.reject(error)
})

export const errorMessage = (error) => {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) {
    return detail.map(item => {
      const field = item.loc?.filter(part => part !== 'body').at(-1)
      return `${field ? `${String(field).replaceAll('_',' ')}: ` : ''}${item.msg}`
    }).join(' · ')
  }
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') return detail.message || JSON.stringify(detail)
  return error.message || 'Something went wrong'
}
export default api
