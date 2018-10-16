/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.common.emme2.io;

/** Holds the global parameters for an Emme2 databank.
 * 
 * History: 
 * Originally written in C by Tim Heier and then ported to Java 
 * by Joel Freedman.
 *
 * @author    Tim Heier, Joel Freedman
 * @version   1.0, 9/19/2002
 */
public class GlobalDatabankParameters {

  public int LDI,LDO,LGI,LGO,LDAI,LDAO,LERO,LLIO,LREP,LGRAPH,
      KMOD,IDEV,ISHORT,LPSIZ,IPGE,IDAT,IUSR,ITPTER,ITPPRI,ITPPLO,
      IDM31,IDM32,IGCMD,ICPDAT,ISCEN,IMODL,LMODL,ICGM,IMFB,IEROP,
      KLU,KCU,KEU,IDM44,IDM45,IDM46,IDM47,IDM48,IDM49,IDBREL,MSCEN,
      MCENT,MNODE,MLINK,MTURN,MLINE,MLSEG,MMAT,MFUNC,MOPER;

  public int[] IPHYS = new int[10+1];
  
  public GlobalDatabankParameters() {
  }

}