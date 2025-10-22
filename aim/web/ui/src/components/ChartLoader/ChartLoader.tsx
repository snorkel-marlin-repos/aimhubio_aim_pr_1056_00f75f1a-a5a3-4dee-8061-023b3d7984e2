import React from 'react';
import _ from 'lodash-es';

import { Skeleton } from '@material-ui/lab';

import { IChartLoaderProps } from 'types/components/ChartLoader/ChartLoader';

import './ChartLoader.scss';

function ChartLoader({
  controlsCount = 3,
}: IChartLoaderProps): React.FunctionComponentElement<React.ReactNode> {
  return (
    <div className='ChartLoader'>
      <div className='ChartLoader__chart'>
        <span>Loading...</span>
      </div>
      {!_.isEmpty(controlsCount) && (
        <div className='ChartLoader__controls'>
          {[...Array(controlsCount)].map((i, index) => (
            <Skeleton
              key={index}
              variant='rect'
              style={{ minHeight: 35, height: 35, width: 35, minWidth: 35 }}
              animation='wave'
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default ChartLoader;
