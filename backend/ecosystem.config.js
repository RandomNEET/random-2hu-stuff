module.exports = {
  apps: [{
    name: 'r2s-api',
    script: 'server.cjs',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    env_production: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: '/var/log/pm2/r2s-api.error.log',
    out_file: '/var/log/pm2/r2s-api.out.log',
    log_file: '/var/log/pm2/r2s-api.log',
    time: true,
    
    // 监控配置
    monitoring: false,
    
    // 自动重启配置
    min_uptime: '10s',
    max_restarts: 10,
    
    // 集群配置（如果需要）
    // instances: 'max',
    // exec_mode: 'cluster'
  }]
}
