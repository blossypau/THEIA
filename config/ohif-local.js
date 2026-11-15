window.config = {
  routerBasename: '/', extensions: [], modes: [],
  showStudyList: true, showLoadingIndicator: true,
  showWarningMessageForCrossOrigin: true, showCPUFallbackMessage: true,
  maxNumberOfWebWorkers: 2,
  defaultDataSourceName: 'dicomlocal',
  dataSources: [{
    namespace: '@ohif/extension-default.dataSourcesModule.dicomlocal',
    sourceName: 'dicomlocal',
    configuration: { friendlyName: 'Local files only' }
  }]
};
