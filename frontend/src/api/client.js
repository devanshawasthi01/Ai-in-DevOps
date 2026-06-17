import axios from 'axios'

const client = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 300_000, // 5 min — LLM can be slow
})

export default client
