import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useWebSocketStore = defineStore('websocket', () => {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const signals = ref<any[]>([])
  const marketData = ref<Record<string, any>>({})
  const liveMonitoring = ref(false)

  const isConnected = computed(() => connected.value)
  const latestSignals = computed(() => signals.value.slice(0, 10))

  function connect() {
    const wsUrl = `ws://localhost:9000/api/v1/live/ws`

    try {
      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        console.log('WebSocket connected')
        connected.value = true

        ws.value?.send(JSON.stringify({
          action: 'subscribe',
          symbols: ['600519.SH', '000858.SZ', '300750.SZ', '000333.SZ', '002594.SZ']
        }))
      }

      ws.value.onmessage = (event) => {
        const data = JSON.parse(event.data)
        handleMessage(data)
      }

      ws.value.onclose = () => {
        console.log('WebSocket disconnected')
        connected.value = false
        setTimeout(connect, 5000)
      }

      ws.value.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to connect:', error)
    }
  }

  function handleMessage(data: any) {
    switch (data.type) {
      case 'market_data':
        marketData.value[data.symbol] = data.data
        break
      case 'signal':
        signals.value.unshift(data)
        if (signals.value.length > 50) {
          signals.value = signals.value.slice(0, 50)
        }
        break
      case 'trade':
        console.log('Trade:', data)
        break
    }
  }

  function send(message: any) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message))
    }
  }

  function startLiveMonitoring() {
    liveMonitoring.value = true
    send({ action: 'start_monitoring' })
  }

  function stopLiveMonitoring() {
    liveMonitoring.value = false
    send({ action: 'stop_monitoring' })
  }

  function disconnect() {
    ws.value?.close()
  }

  return {
    ws,
    connected,
    signals,
    marketData,
    liveMonitoring,
    isConnected,
    latestSignals,
    connect,
    disconnect,
    send,
    startLiveMonitoring,
    stopLiveMonitoring
  }
})
