<template>
  <header>
    <h1>MyLudo</h1>
  </header>
  <main>
    <RouterView />
  </main>
</template>

<style>
:root {
  font-family: system-ui, sans-serif;
  color-scheme: light dark;
}
body {
  margin: 0;
}
header,
main {
  padding: 0 16px;
  max-width: 960px;
  margin: 0 auto;
}
</style>
