// ============================================================
// DIAGNÓSTICO DE DADOS - FIFA World Cup 2026
// ============================================================

console.log('🔍 Iniciando diagnóstico...\n');

// 1. Verificar estrutura dos arquivos
async function diagnose() {
  const results = {};
  
  // Testar cada endpoint
  const endpoints = [
    '/api/meta',
    '/api/stats',
    '/api/filter?limit=5',
    '/api/simulation/0'
  ];
  
  for (const url of endpoints) {
    console.log(`📡 Testando: ${url}`);
    try {
      const response = await fetch(url);
      console.log(`  Status: ${response.status} ${response.statusText}`);
      console.log(`  Content-Type: ${response.headers.get('content-type')}`);
      
      if (!response.ok) {
        console.error(`  ❌ ERRO: ${response.status}`);
        results[url] = { error: `HTTP ${response.status}` };
        continue;
      }
      
      const data = await response.json();
      
      // Analisar estrutura
      if (url === '/api/meta') {
        console.log(`  Keys:`, Object.keys(data));
        console.log(`  Champions sample:`, data.champions?.slice(0, 3));
        console.log(`  Teams count:`, data.teams?.length);
        console.log(`  Combinations count:`, data.combinations?.length);
      }
      
      if (url === '/api/stats') {
        const teams = Object.keys(data);
        console.log(`  Teams count:`, teams.length);
        if (teams.length > 0) {
          const firstTeam = teams[0];
          console.log(`  Sample team: ${firstTeam}`, Object.keys(data[firstTeam]));
        }
      }
      
      if (url === '/api/filter?limit=5') {
        console.log(`  Total results:`, data.total);
        console.log(`  Results count:`, data.results?.length);
        if (data.results?.length > 0) {
          console.log(`  Sample result:`, data.results[0]);
          console.log(`  Result keys:`, Object.keys(data.results[0]));
        }
      }
      
      if (url === '/api/simulation/0') {
        console.log(`  Keys:`, Object.keys(data));
        if (data.summary) {
          console.log(`  Summary:`, data.summary);
        }
        if (data.bracket) {
          console.log(`  Bracket keys:`, Object.keys(data.bracket));
          console.log(`  Rounds:`, Object.keys(data.bracket.rounds || {}));
        }
        if (data.groups) {
          console.log(`  Groups type:`, Array.isArray(data.groups) ? 'Array' : typeof data.groups);
          if (Array.isArray(data.groups)) {
            console.log(`  Groups count:`, data.groups.length);
            if (data.groups[0]) {
              console.log(`  First group keys:`, Object.keys(data.groups[0]));
            }
          }
        }
      }
      
      results[url] = { success: true, type: typeof data, sampleKeys: Object.keys(data).slice(0, 10) };
      
    } catch (error) {
      console.error(`  ❌ ERRO:`, error.message);
      results[url] = { error: error.message };
    }
    console.log('');
  }
  
  // 2. Verificar se os elementos DOM existem
  console.log('📋 Verificando elementos DOM...');
  const domIds = [
    'metrics', 'resultsTable', 'championDistribution', 
    'bracketGrid', 'groupsGrid', 'classifiedTable',
    'championFilter', 'combinationFilter', 'thirdGroupFilter',
    'teamFilter', 'stageFilter', 'simulationSelect',
    'filterSummary', 'selectedSimulationTag',
    'summaryContent', 'resultCount',
    'compareTeam1', 'compareTeam2', 'compareResults',
    'quickSearch', 'statsTable'
  ];
  
  const missingElements = [];
  domIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) {
      missingElements.push(id);
      console.error(`  ❌ Elemento #${id} NÃO encontrado`);
    }
  });
  
  if (missingElements.length === 0) {
    console.log('  ✅ Todos elementos DOM encontrados');
  } else {
    console.error(`  ❌ ${missingElements.length} elementos faltando:`, missingElements);
  }
  
  // 3. Verificar estado atual
  console.log('\n📊 Estado atual:');
  console.log('  Meta carregado:', !!state.meta);
  console.log('  Stats carregado:', !!state.stats);
  console.log('  Filtered length:', state.filtered?.length || 0);
  console.log('  Selected simulation:', state.selectedSimulation);
  console.log('  Current simulation:', !!state.currentSimulation);
  
  // 4. Sugestões baseadas nos resultados
  console.log('\n💡 Diagnóstico:');
  
  if (!results['/api/meta']?.success) {
    console.error('  ❌ API /api/meta não está respondendo');
    console.log('  → Verifique se o servidor está rodando (node dash/site_server.mjs)');
    console.log('  → Verifique se a porta está correta');
  }
  
  if (missingElements.length > 0) {
    console.error(`  ❌ Elementos DOM faltando no HTML`);
    console.log('  → Verifique se o HTML tem os IDs corretos');
  }
  
  if (!state.meta && results['/api/meta']?.success) {
    console.error('  ❌ Dados carregados mas não atribuídos ao state');
    console.log('  → Verifique a função init()');
  }
  
  // 5. Teste rápido de renderização
  console.log('\n🧪 Teste de renderização:');
  try {
    if (typeof flag === 'function') {
      console.log('  ✅ Função flag() funciona:', flag('Brazil'));
    } else {
      console.error('  ❌ Função flag() não definida');
    }
    
    if (typeof renderMetrics === 'function') {
      console.log('  ✅ Função renderMetrics() definida');
    } else {
      console.error('  ❌ Função renderMetrics() não definida');
    }
    
    if (typeof renderBracket === 'function') {
      console.log('  ✅ Função renderBracket() definida');
    } else {
      console.error('  ❌ Função renderBracket() não definida');
    }
  } catch (e) {
    console.error('  ❌ Erro em funções:', e.message);
  }
  
  return results;
}

// Executar diagnóstico
console.log('='.repeat(60));
console.log('DIAGNÓSTICO FIFA WORLD CUP 2026');
console.log('='.repeat(60) + '\n');

diagnose().then(results => {
  console.log('\n' + '='.repeat(60));
  console.log('RESUMO:');
  
  const apisOk = Object.values(results).filter(r => r.success).length;
  const apisTotal = Object.keys(results).length;
  
  console.log(`  APIs funcionando: ${apisOk}/${apisTotal}`);
  
  // Salvar resultados para debug
  window.__diagnosticResults = results;
  console.log('\n  💾 Resultados salvos em window.__diagnosticResults');
  console.log('  📋 Cole o resultado completo para análise');
});